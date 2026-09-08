# app/routers/team.py
import os
import secrets
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_current_user, resolve_account_company, owner_has_tier
from ..security import get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from ..email.service import send_email, render_template

load_dotenv()

router = APIRouter()

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


def _client_role_id(db: Session):
    role = db.query(models.Role).filter(models.Role.Name == "Client").first()
    return role.Id if role else None


@router.get("/members", response_model=schemas.TeamListResponse)
def list_members(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    is_owner = company.OwnerUserId == current_user.Id
    owner_user = db.query(models.User).filter(models.User.Id == company.OwnerUserId).first()

    rows = (
        db.query(models.AccountMember)
        .filter(models.AccountMember.CompanyId == company.Id, models.AccountMember.Status != "revoked")
        .order_by(models.AccountMember.Created.asc())
        .all()
    )

    members = []
    for m in rows:
        display_name = None
        if m.MemberUserId:
            member_user = db.query(models.User).filter(models.User.Id == m.MemberUserId).first()
            display_name = member_user.DisplayName if member_user else None
        members.append(schemas.TeamMemberRead(
            id=m.Id, email=m.InviteEmail, display_name=display_name, status=m.Status, created=m.Created,
        ))

    # Show the owner themselves as an implicit first row.
    owner_row = schemas.TeamMemberRead(
        id=0,
        email=owner_user.Email if owner_user else "",
        display_name=f"{owner_user.DisplayName} (Owner)" if owner_user else "Owner",
        status="active",
        created=owner_user.Created if owner_user else company.Created,
    )
    tier_eligible = owner_has_tier(db, company, "Business")
    return schemas.TeamListResponse(is_owner=is_owner, tier_eligible=tier_eligible, members=[owner_row] + members)


@router.post("/invite", response_model=schemas.TeamMemberRead, status_code=201)
def invite_member(
    req: schemas.TeamInviteRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    if company.OwnerUserId != current_user.Id:
        raise HTTPException(403, "Only the account owner can invite team members")

    if not owner_has_tier(db, company, "Business"):
        raise HTTPException(403, "Upgrade to Business to invite team members.")

    if req.email.lower() == current_user.Email.lower():
        raise HTTPException(400, "You can't invite yourself")

    existing_invite = (
        db.query(models.AccountMember)
        .filter(
            models.AccountMember.CompanyId == company.Id,
            models.AccountMember.InviteEmail == req.email,
            models.AccountMember.Status != "revoked",
        )
        .first()
    )
    if existing_invite:
        raise HTTPException(400, "This email is already part of your team")

    existing_user = db.query(models.User).filter(models.User.Email == req.email).first()
    company_name = company.Name or "their company"

    if existing_user:
        already_member_elsewhere = (
            db.query(models.AccountMember)
            .filter(models.AccountMember.MemberUserId == existing_user.Id, models.AccountMember.Status == "active")
            .first()
        )
        if already_member_elsewhere:
            raise HTTPException(400, "This email is already a team member of another WelcoChat account")

        if existing_user.CompanyId and existing_user.CompanyId != company.Id:
            owns_subscription = (
                db.query(models.Subscription)
                .filter(models.Subscription.CompanyId == existing_user.CompanyId)
                .first()
            )
            if owns_subscription:
                raise HTTPException(400, "This email already has its own WelcoChat subscriptions — it can't also join as a team member")

        member = models.AccountMember(
            CompanyId=company.Id,
            MemberUserId=existing_user.Id,
            InviteEmail=req.email,
            Status="active",
        )
        db.add(member)
        existing_user.CompanyId = company.Id
        db.commit()
        db.refresh(member)

        html_body = f"<p>You've been added to {company_name}'s WelcoChat account. Log in as usual at {FRONTEND_BASE_URL} to see their subscriptions.</p>"
        send_email(
            subject="You've been added to a WelcoChat team",
            email_to=existing_user.Email,
            html_body=html_body,
            text_body=f"You've been added to {company_name}'s WelcoChat account. Log in at {FRONTEND_BASE_URL}.",
        )
        return schemas.TeamMemberRead(
            id=member.Id, email=member.InviteEmail, display_name=existing_user.DisplayName,
            status=member.Status, created=member.Created,
        )

    token = secrets.token_hex(16)
    member = models.AccountMember(
        CompanyId=company.Id,
        InviteEmail=req.email,
        InviteToken=token,
        Status="invited",
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    accept_url = f"{FRONTEND_BASE_URL}/accept-invite?token={token}"
    html_body = render_template("team_invite.html", company_name=company_name, accept_url=accept_url)
    send_email(
        subject=f"You're invited to join {company_name} on WelcoChat",
        email_to=req.email,
        html_body=html_body,
        text_body=f"You've been invited to join {company_name}'s WelcoChat account: {accept_url}",
    )

    return schemas.TeamMemberRead(
        id=member.Id, email=member.InviteEmail, display_name=req.name, status=member.Status, created=member.Created,
    )


@router.delete("/members/{member_id}", status_code=204)
def remove_member(
    member_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    if company.OwnerUserId != current_user.Id:
        raise HTTPException(403, "Only the account owner can remove team members")

    member = (
        db.query(models.AccountMember)
        .filter(models.AccountMember.Id == member_id, models.AccountMember.CompanyId == company.Id)
        .first()
    )
    if member is None:
        raise HTTPException(404, "Team member not found")

    member.Status = "revoked"
    db.commit()


@router.get("/invite/{token}", response_model=schemas.InviteDetailsRead)
def get_invite_details(token: str, db: Session = Depends(get_db)):
    member = (
        db.query(models.AccountMember)
        .filter(models.AccountMember.InviteToken == token, models.AccountMember.Status == "invited")
        .first()
    )
    if member is None:
        raise HTTPException(404, "Invalid or expired invite")

    company = db.query(models.Company).filter(models.Company.Id == member.CompanyId).first()
    # Field name kept as owner_display_name for API/frontend compatibility —
    # it now carries the company's name, not a person's, which still reads
    # correctly in "Join {name}'s WelcoChat account".
    return schemas.InviteDetailsRead(
        invite_email=member.InviteEmail,
        owner_display_name=company.Name if company and company.Name else "This team",
    )


@router.post("/accept-invite", response_model=schemas.Token)
def accept_invite(req: schemas.AcceptInviteRequest, db: Session = Depends(get_db)):
    member = (
        db.query(models.AccountMember)
        .filter(models.AccountMember.InviteToken == req.token, models.AccountMember.Status == "invited")
        .first()
    )
    if member is None:
        raise HTTPException(404, "Invalid or expired invite")

    existing_user = db.query(models.User).filter(models.User.Email == member.InviteEmail).first()
    if existing_user is not None:
        raise HTTPException(400, "An account with this email already exists — please log in instead")

    user = models.User(
        DisplayName=req.display_name,
        Email=member.InviteEmail,
        HashedPassword=get_password_hash(req.password),
        IsActive=True,
        RoleId=_client_role_id(db),
        # Joins the inviting company directly — they do not get their own
        # new Company (that's what ensure_company is for, on the signup
        # paths that don't come through an invite).
        CompanyId=member.CompanyId,
    )
    db.add(user)
    db.flush()

    member.MemberUserId = user.Id
    member.Status = "active"
    member.AcceptedAt = datetime.utcnow()
    db.commit()

    access_token = create_access_token(
        data={"sub": user.Email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}
