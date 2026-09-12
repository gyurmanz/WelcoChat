# app/routers/contact.py
import os
import html
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_current_user, resolve_account_company
from ..email.service import send_email

router = APIRouter()

# Hova menjenek a welcochat.com landing-oldal demo-kerelmei (env-bol felulirhato).
CONTACT_TO = os.getenv("CONTACT_TO", "info@welcochat.com")


@router.post("/contact")
def submit_contact(req: schemas.ContactRequest):
    def esc(v: str) -> str:
        return html.escape(v or "")

    rows = [
        ("Name", req.name),
        ("Company", req.company),
        ("Email", req.email),
        ("Website", req.website or "-"),
        ("Phone", req.phone or "-"),
        ("Service", req.service or "-"),
        ("Approx. volume", req.volume or "-"),
        ("Preferred pilot", req.pilot_type or "-"),
    ]
    html_rows = "".join(
        f"<tr><td style='padding:4px 10px;color:#64748b'>{esc(k)}</td>"
        f"<td style='padding:4px 10px'><strong>{esc(str(v))}</strong></td></tr>"
        for k, v in rows
    )
    html_body = (
        "<h2>New pilot request from kaptila.com</h2>"
        f"<table>{html_rows}</table>"
        f"<p><strong>Workflow to improve:</strong><br/>{esc(req.message or '-')}</p>"
    )
    text_body = (
        "New pilot request from kaptila.com\n\n"
        + "\n".join(f"{k}: {v}" for k, v in rows)
        + f"\n\nWorkflow to improve:\n{req.message or '-'}"
    )

    try:
        send_email(
            subject=f"New pilot request: {req.name} ({req.company})",
            email_to=CONTACT_TO,
            html_body=html_body,
            text_body=text_body,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Could not send your request. Please try again later.",
        ) from e

    return {"message": "received"}


# --- Authenticated in-product support ---------------------------------------
# Until this existed, a signed-in customer who hit a bug had nowhere in the
# product to say so — only the public pre-sales form on the marketing site.

_SUPPORT_TOPICS = {
    "bug": "Bug report",
    "idea": "Feature idea",
    "question": "Question",
}

_SUPPORT_MAX_PER_HOUR = 10
_support_hits: dict[int, deque] = defaultdict(deque)


def _support_rate_limited(user_id: int) -> bool:
    hits = _support_hits[user_id]
    now = time.monotonic()
    while hits and now - hits[0] > 3600:
        hits.popleft()
    if len(hits) >= _SUPPORT_MAX_PER_HOUR:
        return True
    hits.append(now)
    return False


@router.post("/support")
def submit_support_request(
    req: schemas.SupportRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.topic not in _SUPPORT_TOPICS:
        raise HTTPException(400, "Unknown topic")
    if _support_rate_limited(current_user.Id):
        raise HTTPException(429, "You've sent several messages recently — please give us a moment to reply.")

    def esc(v) -> str:
        return html.escape(str(v or "-"))

    # Attach the account context automatically. Without it every reply starts
    # with "which plan are you on?" — the customer already told us by logging in.
    company = resolve_account_company(db, current_user)
    subscription = (
        db.query(models.Subscription)
        .filter(models.Subscription.CompanyId == company.Id)
        .order_by(models.Subscription.Created.desc())
        .first()
    )
    plan = "-"
    if subscription is not None:
        service = db.query(models.Service).filter(models.Service.Id == subscription.ServiceId).first()
        plan = f"{service.Tier if service else '?'} ({subscription.Status})"

    rows = [
        ("Type", _SUPPORT_TOPICS[req.topic]),
        ("From", f"{current_user.DisplayName} <{current_user.Email}>"),
        ("Company", company.Name),
        ("Plan", plan),
    ]
    html_rows = "".join(
        f"<tr><td style='padding:4px 10px;color:#64748b'>{esc(k)}</td>"
        f"<td style='padding:4px 10px'><strong>{esc(v)}</strong></td></tr>"
        for k, v in rows
    )
    html_body = (
        f"<h2>{esc(_SUPPORT_TOPICS[req.topic])}: {esc(req.subject)}</h2>"
        f"<table>{html_rows}</table>"
        f"<p style='white-space:pre-wrap'>{esc(req.message)}</p>"
    )
    text_body = (
        f"{_SUPPORT_TOPICS[req.topic]}: {req.subject}\n\n"
        + "\n".join(f"{k}: {v}" for k, v in rows)
        + f"\n\n{req.message}"
    )

    try:
        send_email(
            subject=f"[{_SUPPORT_TOPICS[req.topic]}] {req.subject}",
            email_to=CONTACT_TO,
            html_body=html_body,
            text_body=text_body,
            reply_to=current_user.Email,
        )
    except Exception as e:
        raise HTTPException(500, "Could not send your message. Please try again shortly.") from e

    return {"message": "received"}
