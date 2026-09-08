# app/deps.py
from datetime import datetime
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import SessionLocal
from . import models
from .security import SECRET_KEY, ALGORITHM


# Ez mondja meg FastAPI-nak, hogy hol lehet tokent szerezni (login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="The user could not be identified.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(models.User)
        .filter(models.User.Email == email)
        .first()
    )

    if user is None:
        raise credentials_exception

    return user


_TIER_RANK = {"Basic": 0, "Business": 1, "Enterprise": 2}


def ensure_company(db: Session, user: models.User) -> models.Company:
    """Every User belongs to exactly one Company — their own (created here,
    the first time it's needed) or one they joined via a team invite (set at
    accept-invite time). This is the self-healing fallback; the normal path
    is auth.py creating it immediately at signup."""
    if user.CompanyId:
        company = db.query(models.Company).filter(models.Company.Id == user.CompanyId).first()
        if company:
            return company
    # Name intentionally blank, not user.DisplayName — the billing-details
    # flow (AddSubscriptionView) gates on `!company.name` to ask for a real
    # company name before checkout; a placeholder here would silently skip
    # that step.
    company = models.Company(Name="", OwnerUserId=user.Id)
    db.add(company)
    db.flush()
    user.CompanyId = company.Id
    db.commit()
    db.refresh(company)
    return company


def resolve_account_company(db: Session, current_user: models.User) -> models.Company:
    """The Company whose subscriptions/billing/services current_user should
    see — their own, or the one they joined as a team member (both cases are
    just current_user.CompanyId, set at signup or at accept-invite time)."""
    return ensure_company(db, current_user)


def owner_has_tier(db: Session, company: models.Company, min_tier: str, service_key: str | None = None) -> bool:
    """Account-wide check (used for Team accounts): true if the company has at
    least one subscription — optionally scoped to one product — whose plan
    tier meets or exceeds min_tier."""
    query = (
        db.query(models.Service.Tier)
        .join(models.Subscription, models.Subscription.ServiceId == models.Service.Id)
        .filter(models.Subscription.CompanyId == company.Id)
    )
    if service_key is not None:
        query = query.filter(models.Service.ServiceKey == service_key)
    min_rank = _TIER_RANK.get(min_tier, 0)
    return any(_TIER_RANK.get(tier, 0) >= min_rank for (tier,) in query.all())


def instance_tier(db: Session, instance: models.ServiceInstance) -> str:
    """The plan tier (Basic/Business/Enterprise) of the subscription this
    instance belongs to. Defaults to 'Basic' if anything is missing."""
    subscription = db.query(models.Subscription).filter(models.Subscription.Id == instance.SubscriptionId).first()
    if subscription is None or subscription.ServiceId is None:
        return "Basic"
    service = db.query(models.Service).filter(models.Service.Id == subscription.ServiceId).first()
    return service.Tier if service else "Basic"


def instance_has_tier(db: Session, instance: models.ServiceInstance, min_tier: str) -> bool:
    return _TIER_RANK.get(instance_tier(db, instance), 0) >= _TIER_RANK.get(min_tier, 0)


def instance_subscription_active(db: Session, instance: models.ServiceInstance) -> bool:
    """Whether the subscription behind this instance should still serve public
    (visitor-facing) widget traffic — trial/paid, not past_due/canceled/etc."""
    subscription = db.query(models.Subscription).filter(models.Subscription.Id == instance.SubscriptionId).first()
    if subscription is None:
        return False
    if subscription.Status == "active":
        return True
    if subscription.Status == "trialing":
        # Belt-and-braces: don't trust "trialing" forever if the trial end date
        # has clearly passed — covers a missed/late Stripe webhook, or a
        # subscription where Stripe was never wired up in the first place.
        if subscription.TrialEndsAt and subscription.TrialEndsAt < datetime.utcnow():
            return False
        return True
    return False  # past_due, canceled, unpaid, paused, incomplete, incomplete_expired, etc.
