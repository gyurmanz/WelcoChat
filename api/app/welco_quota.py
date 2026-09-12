# app/welco_quota.py
"""Monthly conversation allowance: the one place that decides how much of a
plan a customer has used. Both the widget (which enforces it) and the portal's
statistics (which display it) call in here, so what a customer is shown and
what actually gets cut off can't drift apart."""
import logging
from datetime import datetime

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from . import models
from .email.service import send_email

logger = logging.getLogger(__name__)


# Plans are sold per conversation/month. We keep serving past the included
# allowance up to this multiple so nobody's widget dies mid-campaign over a
# small overshoot, then stop offering AI answers (the widget falls back to
# putting the visitor in touch with a human, which costs us nothing).
QUOTA_GRACE = 1.2


def month_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)


def conversation_limit_for_instance(db: Session, instance: models.ServiceInstance) -> int | None:
    """Conversations/month included in this instance's plan, or None if the
    plan is unmetered or can't be resolved (fail open — never cut someone off
    because of a missing row)."""
    subscription = db.query(models.Subscription).filter(models.Subscription.Id == instance.SubscriptionId).first()
    if subscription is None or subscription.ServiceId is None:
        return None
    service = db.query(models.Service).filter(models.Service.Id == subscription.ServiceId).first()
    return service.MonthlyConversationLimit if service else None


def conversations_this_month(db: Session, service_instance_id: int) -> int:
    return (
        db.query(func.count(distinct(models.WelcoInteraction.SessionId)))
        .filter(
            models.WelcoInteraction.ServiceInstanceId == service_instance_id,
            models.WelcoInteraction.Created >= month_start(),
            models.WelcoInteraction.SessionId.isnot(None),
        )
        .scalar()
    ) or 0


def session_already_counted(db: Session, service_instance_id: int, session_id: str) -> bool:
    """A conversation already inside this month's count keeps working even once
    the allowance is used up — we cut off new conversations, not ones a visitor
    is in the middle of."""
    if not session_id:
        return False
    return db.query(
        db.query(models.WelcoInteraction)
        .filter(
            models.WelcoInteraction.ServiceInstanceId == service_instance_id,
            models.WelcoInteraction.SessionId == session_id,
            models.WelcoInteraction.Created >= month_start(),
        )
        .exists()
    ).scalar()


def notify_quota_reached(db: Session, instance: models.ServiceInstance, used: int, limit: int) -> None:
    """Emails the account owner the first time a month's allowance runs out.
    Best-effort and once per month — a failure here must never break a reply."""
    month = month_start().strftime("%Y-%m")
    if instance.QuotaNoticeMonth == month:
        return
    instance.QuotaNoticeMonth = month
    db.commit()

    try:
        subscription = db.query(models.Subscription).filter(models.Subscription.Id == instance.SubscriptionId).first()
        company = db.query(models.Company).filter(models.Company.Id == subscription.CompanyId).first() if subscription else None
        owner = db.query(models.User).filter(models.User.Id == company.OwnerUserId).first() if company else None
        if owner is None or not owner.Email:
            return
        send_email(
            subject="Your WelcoChat conversation allowance is used up",
            email_to=owner.Email,
            html_body=(
                f"<p>Your plan includes {limit:,} conversations per month, and "
                f"{instance.ServiceName} has now handled {used:,} this month.</p>"
                f"<p>Your agent keeps answering for a short grace period. After that it will "
                f"stop giving AI answers until the next billing month and offer visitors your "
                f"human contact options instead.</p>"
                f"<p>Upgrading your plan in the WelcoChat portal lifts the limit immediately.</p>"
            ),
        )
    except Exception:
        logger.exception("Failed to send quota notice for ServiceInstance %s", instance.Id)
