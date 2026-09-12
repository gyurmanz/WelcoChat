#!/usr/bin/env python3
"""Daily background chores. Run once a day from cron:

    /home/welcocha/virtualenv/welcochat-api/3.12/bin/python \
        /home/welcocha/welcochat-api/scripts/daily_maintenance.py

Everything here is idempotent and safe to run more than once a day — each task
guards against repeating itself (a sent flag, a freshness check), because a
cron that fires twice must not email a customer twice.
"""
import logging
import os
import sys
import warnings
from datetime import datetime, time, timedelta

# Every datetime in this schema is naive UTC (see models.py), so utcnow() is the
# right call here — an aware datetime would raise on comparison with a stored
# column. Silence 3.12's deprecation notice so cron doesn't email it daily.
warnings.filterwarnings("ignore", category=DeprecationWarning, message=r".*utcnow.*")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402
from app.email.service import send_trial_ending_email  # noqa: E402
from app.welco_crawler import crawl_site  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("maintenance")

# Two nudges: one with enough time to act, one final reminder.
TRIAL_REMINDER_DAYS = (3, 1)
RECRAWL_AFTER_DAYS = 30
# How long conversation/lead content lives on after a subscription ends. The
# privacy policy promises deletion "within a reasonable period after
# cancellation" — this is what actually makes that true.
RETENTION_DAYS_AFTER_END = 90


def send_trial_reminders(db) -> int:
    sent = 0
    now = datetime.utcnow()
    for days_left in TRIAL_REMINDER_DAYS:
        # Match the whole calendar day N days out, not an exact instant — this
        # job runs once a day, so "ends in 3 days" has to mean the day, or a
        # trial whose end time is minutes off the cron time is skipped forever.
        target_day = (now + timedelta(days=days_left)).date()
        window_start = datetime.combine(target_day, time.min)
        window_end = window_start + timedelta(days=1)
        subs = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.Status == "trialing",
                models.Subscription.TrialEndsAt >= window_start,
                models.Subscription.TrialEndsAt < window_end,
            )
            .all()
        )
        for sub in subs:
            marker = f"trial-{days_left}d"
            if (sub.TrialReminderSent or "") == marker:
                continue
            company = db.query(models.Company).filter(models.Company.Id == sub.CompanyId).first()
            owner = db.query(models.User).filter(models.User.Id == company.OwnerUserId).first() if company else None
            if owner is None or not owner.Email:
                continue
            try:
                send_trial_ending_email(
                    email_to=owner.Email,
                    display_name=owner.DisplayName,
                    days_left=days_left,
                    trial_end_date=sub.TrialEndsAt.strftime("%d %B %Y"),
                )
                sub.TrialReminderSent = marker
                db.commit()
                sent += 1
            except Exception:
                db.rollback()
                logger.exception("Trial reminder failed for Subscription %s", sub.Id)
    return sent


def refresh_stale_knowledge_bases(db) -> int:
    """Re-crawls sites nobody has refreshed in a month, so an agent doesn't keep
    quoting prices the customer changed weeks ago. Only touches live agents."""
    cutoff = datetime.utcnow() - timedelta(days=RECRAWL_AFTER_DAYS)
    refreshed = 0
    kbs = (
        db.query(models.WelcoKnowledgeBase)
        .filter(
            models.WelcoKnowledgeBase.Status == "ready",
            models.WelcoKnowledgeBase.SourceUrl.isnot(None),
            models.WelcoKnowledgeBase.CrawledAt < cutoff,
        )
        .all()
    )
    for kb in kbs:
        instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
        if instance is None:
            continue
        subscription = db.query(models.Subscription).filter(models.Subscription.Id == instance.SubscriptionId).first()
        if subscription is None or subscription.Status not in ("active", "trialing"):
            continue
        try:
            content, page_count = crawl_site(kb.SourceUrl)
            kb.Content = content
            kb.PageCount = page_count
            kb.CrawledAt = datetime.utcnow()
            kb.ErrorMessage = None
            db.commit()
            refreshed += 1
            logger.info("Re-crawled KB %s (%s pages)", kb.Id, page_count)
        except Exception as exc:  # noqa: BLE001 — one bad site must not stop the rest
            db.rollback()
            # Deliberately leave Status "ready": the previous crawl is still
            # serving fine, and a temporarily unreachable site shouldn't take a
            # working agent offline.
            logger.warning("Re-crawl failed for KB %s (%s): %s", kb.Id, kb.SourceUrl, exc)
    return refreshed


def purge_expired_data(db) -> int:
    """Deletes visitor conversations and leads belonging to subscriptions that
    ended more than RETENTION_DAYS_AFTER_END ago."""
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS_AFTER_END)
    deleted = 0
    dead_subs = (
        db.query(models.Subscription)
        .filter(
            models.Subscription.Status.in_(("canceled", "cancelled", "unpaid", "incomplete_expired")),
            models.Subscription.EndDate.isnot(None),
            models.Subscription.EndDate < cutoff,
        )
        .all()
    )
    for sub in dead_subs:
        instances = db.query(models.ServiceInstance).filter(models.ServiceInstance.SubscriptionId == sub.Id).all()
        for instance in instances:
            conv_ids = [
                c.Id for c in db.query(models.WelcoConversation)
                .filter(models.WelcoConversation.ServiceInstanceId == instance.Id).all()
            ]
            if conv_ids:
                db.query(models.WelcoConversationMessage).filter(
                    models.WelcoConversationMessage.ConversationId.in_(conv_ids)
                ).delete(synchronize_session=False)
                db.query(models.WelcoConversation).filter(
                    models.WelcoConversation.Id.in_(conv_ids)
                ).delete(synchronize_session=False)
                deleted += len(conv_ids)
            deleted += db.query(models.WelcoLead).filter(
                models.WelcoLead.ServiceInstanceId == instance.Id
            ).delete(synchronize_session=False)
        db.commit()
    return deleted


def main() -> None:
    db = SessionLocal()
    try:
        logger.info("trial reminders sent: %s", send_trial_reminders(db))
        logger.info("knowledge bases refreshed: %s", refresh_stale_knowledge_bases(db))
        logger.info("expired records purged: %s", purge_expired_data(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
