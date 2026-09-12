# app/routers/stats.py
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from .. import models, schemas
from ..welco_quota import conversation_limit_for_instance, conversations_this_month
from ..deps import get_db, get_current_user, resolve_account_company

router = APIRouter()

_TREND_DAYS = 30


def _daily_series(db: Session, model, instance_id: int, since: datetime) -> list[schemas.DailyCount]:
    day_col = cast(model.Created, Date)
    rows = (
        db.query(day_col.label("day"), func.count().label("count"))
        .filter(model.ServiceInstanceId == instance_id, model.Created >= since)
        .group_by(day_col)
        .all()
    )
    counts = {r.day.isoformat(): r.count for r in rows}
    today = datetime.utcnow().date()
    series = []
    for i in range(_TREND_DAYS - 1, -1, -1):
        d = today - timedelta(days=i)
        series.append(schemas.DailyCount(date=d.isoformat(), count=counts.get(d.isoformat(), 0)))
    return series


def _welco_stats(db: Session, instance: models.ServiceInstance) -> schemas.WelcoStatsRead:
    since = datetime.utcnow() - timedelta(days=_TREND_DAYS)

    total_messages = (
        db.query(func.count())
        .filter(models.WelcoInteraction.ServiceInstanceId == instance.Id)
        .scalar()
    ) or 0
    messages_last_30d = (
        db.query(func.count())
        .filter(models.WelcoInteraction.ServiceInstanceId == instance.Id, models.WelcoInteraction.Created >= since)
        .scalar()
    ) or 0
    handoff_count = (
        db.query(func.count())
        .filter(models.WelcoInteraction.ServiceInstanceId == instance.Id, models.WelcoInteraction.Handoff == True)  # noqa: E712
        .scalar()
    ) or 0
    handoff_rate = round((handoff_count / total_messages) * 100, 1) if total_messages else 0.0

    total_leads = (
        db.query(func.count())
        .filter(models.WelcoLead.ServiceInstanceId == instance.Id)
        .scalar()
    ) or 0
    leads_last_30d = (
        db.query(func.count())
        .filter(models.WelcoLead.ServiceInstanceId == instance.Id, models.WelcoLead.Created >= since)
        .scalar()
    ) or 0

    document_count = (
        db.query(func.count())
        .filter(models.WelcoDocument.ServiceInstanceId == instance.Id)
        .scalar()
    ) or 0

    kb = (
        db.query(models.WelcoKnowledgeBase)
        .filter(models.WelcoKnowledgeBase.ServiceInstanceId == instance.Id)
        .first()
    )

    return schemas.WelcoStatsRead(
        instance_id=instance.Id,
        total_messages=total_messages,
        messages_last_30d=messages_last_30d,
        handoff_rate=handoff_rate,
        total_leads=total_leads,
        leads_last_30d=leads_last_30d,
        page_count=kb.PageCount if kb else None,
        document_count=document_count,
        kb_status=kb.Status if kb else "pending",
        crawled_at=kb.CrawledAt if kb else None,
        daily_messages=_daily_series(db, models.WelcoInteraction, instance.Id, since),
        # Same source of truth the widget's quota check uses, so what the
        # customer sees here is exactly what gets enforced.
        conversations_this_month=conversations_this_month(db, instance.Id),
        conversation_limit=conversation_limit_for_instance(db, instance),
    )


@router.get("", response_model=schemas.StatsResponse)
def get_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    instances = (
        db.query(models.ServiceInstance)
        .join(models.Subscription, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
        .filter(models.Subscription.CompanyId == company.Id)
        .order_by(models.ServiceInstance.Created.asc())
        .all()
    )

    welco = [_welco_stats(db, i) for i in instances if i.ServiceKey == "welco"]

    return schemas.StatsResponse(welco=welco)
