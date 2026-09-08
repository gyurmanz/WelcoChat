# app/push_service.py
"""Web Push (browser Push API) notifications — lets a portal user who has
installed the client portal as a PWA get an OS-level notification when a
live handoff needs attention, without us writing a native mobile app."""
import json
import logging
import os

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from . import models

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").replace("\\n", "\n")
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS_SUB = os.getenv("VAPID_CLAIMS_SUB", "mailto:info@welcochat.com")


def is_configured() -> bool:
    return bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY)


def _send_one(db: Session, sub: models.PushSubscription, title: str, body: str, url: str) -> None:
    try:
        webpush(
            subscription_info={
                "endpoint": sub.Endpoint,
                "keys": {"p256dh": sub.P256dh, "auth": sub.Auth},
            },
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIMS_SUB},
        )
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            # The browser/OS dropped this subscription (uninstalled, expired,
            # permission revoked) — stop trying to send to it.
            db.delete(sub)
            db.commit()
        else:
            logger.warning("Web push failed for subscription %s: %s", sub.Id, exc)
    except Exception:
        logger.exception("Unexpected error sending web push for subscription %s", sub.Id)


def notify_company_users(db: Session, company_id: int, title: str, body: str, url: str = "/portal/live-chat") -> None:
    """Sends a push notification to every user of the given company who has
    an active push subscription (company owner + accepted team members)."""
    if not is_configured():
        return

    owner_id = (
        db.query(models.Company.OwnerUserId)
        .filter(models.Company.Id == company_id)
        .scalar()
    )
    member_ids = [
        row[0]
        for row in db.query(models.AccountMember.MemberUserId)
        .filter(
            models.AccountMember.CompanyId == company_id,
            models.AccountMember.Status == "active",
            models.AccountMember.MemberUserId.isnot(None),
        )
        .all()
    ]
    user_ids = {uid for uid in [owner_id, *member_ids] if uid is not None}
    if not user_ids:
        return

    subs = (
        db.query(models.PushSubscription)
        .filter(models.PushSubscription.UserId.in_(user_ids))
        .all()
    )
    for sub in subs:
        _send_one(db, sub, title, body, url)
