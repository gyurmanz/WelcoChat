# app/routers/subscriptions.py
import json
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, stripe_service
from ..deps import get_db, get_current_user, resolve_account_company, instance_tier, instance_has_tier, _TIER_RANK

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter()

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

_VALID_BILLING = {"monthly", "annual"}
_VALID_SETUP_STATUSES = {
    "not_configured", "setup_in_progress", "pending_review",
    "running", "paused", "error", "cancelled",
}
_TRIAL_DAYS = 14

# Config keys that require a plan tier above Basic — checked whenever a
# ServiceInstance's configuration is saved, regardless of which product it
# belongs to.
# Value is (min_tier, trigger_value) — trigger_value=None means any truthy
# value is gated; otherwise only that exact value is (e.g. the default
# "bottom-right" widget position is never gated, only "bottom-left" is).
_GATED_CONFIG_KEYS = {
    "notification_channel_type": ("Business", None),
    "whatsapp_account_sid": ("Business", None),
    "whatsapp_auth_token": ("Business", None),
    "whatsapp_number": ("Business", None),
    "widget_position": ("Business", "bottom-left"),
    "widget_custom_css": ("Enterprise", None),
}


def _gated_tier_violation(db: Session, instance: models.ServiceInstance, configuration: dict) -> str | None:
    """Returns the minimum tier name required if configuration contains a
    gated value the instance's current plan doesn't cover, else None."""
    for key, (min_tier, trigger_value) in _GATED_CONFIG_KEYS.items():
        value = configuration.get(key)
        if not value or (trigger_value is not None and value != trigger_value):
            continue
        if not instance_has_tier(db, instance, min_tier):
            return min_tier
    return None


def _service_plan_out(s: models.Service) -> schemas.ServicePlanRead:
    return schemas.ServicePlanRead(
        id=s.Id,
        service_key=s.ServiceKey,
        service_name=s.ServiceName,
        tier=s.Tier,
        monthly_price=float(s.MonthlyPrice),
        annual_price=float(s.AnnualPrice),
    )


def _service_instance_out(db: Session, i: models.ServiceInstance) -> schemas.ServiceInstanceRead:
    return schemas.ServiceInstanceRead(
        id=i.Id,
        subscription_id=i.SubscriptionId,
        service_key=i.ServiceKey,
        service_name=i.ServiceName,
        setup_status=i.SetupStatus,
        tier=instance_tier(db, i),
        configuration=json.loads(i.ConfigurationData) if i.ConfigurationData else None,
    )


def _subscription_out(db: Session, sub: models.Subscription, service: "models.Service | None") -> schemas.SubscriptionRead:
    pending_tier = None
    if sub.PendingServiceId is not None:
        pending_service = db.query(models.Service).filter(models.Service.Id == sub.PendingServiceId).first()
        pending_tier = pending_service.Tier if pending_service else None
    return schemas.SubscriptionRead(
        id=sub.Id,
        service_id=sub.ServiceId,
        service_key=service.ServiceKey if service else None,
        service_name=service.ServiceName if service else None,
        tier=service.Tier if service else None,
        billing_period=sub.BillingPeriod,
        paid_price=float(sub.PaidPrice) if sub.PaidPrice is not None else None,
        start_date=sub.StartDate,
        end_date=sub.EndDate,
        trial_ends_at=sub.TrialEndsAt,
        status=sub.Status,
        created=sub.Created,
        pending_tier=pending_tier,
        pending_billing_period=sub.PendingBillingPeriod,
    )


def _has_had_trial(db: Session, company_id: int, service_key: str) -> bool:
    return db.query(models.Subscription).filter(
        models.Subscription.CompanyId == company_id,
        models.Subscription.Type == service_key,
        models.Subscription.TrialEndsAt.isnot(None),
    ).first() is not None


def _company_contact(db: Session, company: models.Company) -> tuple[str, str]:
    """(email, display_name) of the company's designated billing contact —
    used for the Stripe customer record so it stays stable regardless of
    which team member happens to be checking out."""
    owner_user = db.query(models.User).filter(models.User.Id == company.OwnerUserId).first()
    if owner_user is None:
        raise HTTPException(500, "This company has no owner on record — contact support.")
    return owner_user.Email, owner_user.DisplayName


@router.get("/services", response_model=list[schemas.ServicePlanRead])
def list_service_plans(db: Session = Depends(get_db)):
    services = (
        db.query(models.Service)
        .filter(models.Service.IsActive == True)  # noqa: E712
        .order_by(models.Service.SortOrder)
        .all()
    )
    return [_service_plan_out(s) for s in services]


@router.get("", response_model=list[schemas.SubscriptionRead])
def list_subscriptions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    subs = (
        db.query(models.Subscription)
        .filter(models.Subscription.CompanyId == company.Id)
        .order_by(models.Subscription.Created.desc())
        .all()
    )
    service_ids = {s.ServiceId for s in subs if s.ServiceId is not None}
    services = (
        {s.Id: s for s in db.query(models.Service).filter(models.Service.Id.in_(service_ids)).all()}
        if service_ids else {}
    )
    return [_subscription_out(db, sub, services.get(sub.ServiceId)) for sub in subs]


@router.get("/trial-eligibility", response_model=schemas.TrialEligibilityRead)
def trial_eligibility(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    return schemas.TrialEligibilityRead(
        welco=not _has_had_trial(db, company.Id, "welco"),
    )


@router.post("/trial", response_model=schemas.SubscriptionRead, status_code=201)
def create_trial_subscription(
    body: schemas.TrialSubscriptionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)

    if _has_had_trial(db, company.Id, body.service_key):
        raise HTTPException(409, "A free trial has already been used for this product.")

    service = (
        db.query(models.Service)
        .filter(
            models.Service.ServiceKey == body.service_key,
            models.Service.Tier == "Business",
            models.Service.IsActive == True,  # noqa: E712
        )
        .first()
    )
    if service is None:
        raise HTTPException(400, "No matching plan found")

    today = datetime.utcnow()
    billing_period = "monthly"  # trial always starts monthly; switch to annual later via Change Plan
    month = today.month % 12 + 1
    year = today.year + (1 if today.month == 12 else 0)
    end = today.replace(year=year, month=month)
    paid_price = Decimal(str(service.MonthlyPrice))
    trial_ends_at = today + timedelta(days=_TRIAL_DAYS)

    sub = models.Subscription(
        CompanyId=company.Id,
        UserId=current_user.Id,
        Type=service.ServiceKey,
        Status="trialing",
        ServiceId=service.Id,
        BillingPeriod=billing_period,
        PaidPrice=paid_price,
        StartDate=today,
        EndDate=end,
        TrialEndsAt=trial_ends_at,
    )
    db.add(sub)
    db.flush()

    db.add(models.ServiceInstance(
        SubscriptionId=sub.Id,
        ServiceKey=service.ServiceKey,
        ServiceName=service.ServiceName,
        SetupStatus="not_configured",
    ))

    db.commit()
    db.refresh(sub)

    try:
        contact_email, contact_name = _company_contact(db, company)
        stripe_sub_id = stripe_service.create_trial_subscription(
            db, company, contact_email, contact_name, service, billing_period, trial_ends_at
        )
        sub.StripeSubscriptionId = stripe_sub_id
        db.commit()
        db.refresh(sub)
    except Exception:
        logger.exception("Stripe trial subscription creation failed for Subscription %s", sub.Id)

    return _subscription_out(db, sub, service)


@router.post("/checkout", response_model=schemas.CheckoutSessionRead)
def create_checkout(
    body: schemas.CheckoutSessionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.billing_period not in _VALID_BILLING:
        raise HTTPException(400, "Invalid billing_period")

    company = resolve_account_company(db, current_user)

    service = (
        db.query(models.Service)
        .filter(models.Service.Id == body.service_id, models.Service.IsActive == True)  # noqa: E712
        .first()
    )
    if service is None:
        raise HTTPException(400, "No matching plan found")

    price_id = service.StripePriceIdAnnual if body.billing_period == "annual" else service.StripePriceIdMonthly
    if not price_id:
        raise HTTPException(400, f"No Stripe price configured for {service.ServiceKey}/{service.Tier}/{body.billing_period}")

    try:
        contact_email, contact_name = _company_contact(db, company)
        customer_id = stripe_service.get_or_create_customer(db, company, contact_email, contact_name)
        checkout_url = stripe_service.create_checkout_session(
            customer_id=customer_id,
            price_id=price_id,
            client_reference_id=str(company.Id),
            metadata={
                "service_id": str(service.Id),
                "billing_period": body.billing_period,
                "user_id": str(current_user.Id),
            },
            success_url=f"{FRONTEND_BASE_URL}/subscriptions/add?checkout=success&service_key={service.ServiceKey}",
            cancel_url=f"{FRONTEND_BASE_URL}/subscriptions/add?checkout=cancelled",
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to create Stripe Checkout Session for company %s", company.Id)
        raise HTTPException(502, "Failed to start checkout — please try again.")

    return schemas.CheckoutSessionRead(checkout_url=checkout_url)


@router.post("/{subscription_id}/change-plan", response_model=schemas.SubscriptionRead)
def change_plan(
    subscription_id: int,
    body: schemas.ChangePlanRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    sub = (
        db.query(models.Subscription)
        .filter(models.Subscription.Id == subscription_id, models.Subscription.CompanyId == company.Id)
        .first()
    )
    if sub is None:
        raise HTTPException(404, "Subscription not found")

    current_service = db.query(models.Service).filter(models.Service.Id == sub.ServiceId).first()
    if current_service is None:
        raise HTTPException(400, "Current plan not found")

    new_service = (
        db.query(models.Service)
        .filter(models.Service.Id == body.new_service_id, models.Service.IsActive == True)  # noqa: E712
        .first()
    )
    if new_service is None:
        raise HTTPException(400, "No matching plan found")
    if new_service.ServiceKey != current_service.ServiceKey:
        raise HTTPException(400, "Can't change to a different product — start a new subscription instead")

    new_billing_period = body.billing_period or sub.BillingPeriod
    if new_billing_period not in _VALID_BILLING:
        raise HTTPException(400, "Invalid billing_period")
    if new_service.Id == sub.ServiceId and new_billing_period == sub.BillingPeriod:
        if sub.PendingServiceId is None:
            raise HTTPException(400, "This is already your current plan")
        # Re-selecting the current plan cancels a previously scheduled downgrade.
        if sub.StripeSubscriptionId:
            try:
                stripe_service.cancel_scheduled_downgrade(sub.StripeSubscriptionId)
            except Exception:
                logger.exception("Failed to cancel scheduled downgrade for Subscription %s", sub.Id)
                raise HTTPException(502, "Failed to cancel the scheduled downgrade with Stripe — please try again.")
        sub.PendingServiceId = None
        sub.PendingBillingPeriod = None
        db.commit()
        db.refresh(sub)
        return _subscription_out(db, sub, current_service)

    new_price_id = new_service.StripePriceIdAnnual if new_billing_period == "annual" else new_service.StripePriceIdMonthly
    if not new_price_id:
        raise HTTPException(400, f"No Stripe price configured for {new_service.ServiceKey}/{new_service.Tier}/{new_billing_period}")

    if new_billing_period == "annual":
        paid_price = Decimal(str(round(float(new_service.AnnualPrice) * 12, 2)))
    else:
        paid_price = Decimal(str(new_service.MonthlyPrice))

    # A still-trialing subscription hasn't been billed yet, so there's no
    # fairness reason to defer a downgrade — and Stripe actively refuses to
    # attach a Subscription Schedule to one anyway (it's configured to pause
    # at trial end if no payment method is attached). Apply immediately.
    is_downgrade = (
        sub.Status != "trialing"
        and _TIER_RANK.get(new_service.Tier, 0) < _TIER_RANK.get(current_service.Tier, 0)
    )

    if is_downgrade:
        if sub.StripeSubscriptionId:
            try:
                stripe_service.schedule_downgrade(sub.StripeSubscriptionId, new_price_id)
            except Exception:
                logger.exception("Stripe downgrade scheduling failed for Subscription %s", sub.Id)
                raise HTTPException(502, "Failed to schedule the downgrade with Stripe — please try again.")
            sub.PendingServiceId = new_service.Id
            sub.PendingBillingPeriod = new_billing_period
            db.commit()
            db.refresh(sub)
            return _subscription_out(db, sub, current_service)
        else:
            # No live Stripe subscription (best-effort creation failed earlier) — apply directly.
            sub.ServiceId = new_service.Id
            sub.BillingPeriod = new_billing_period
            sub.PaidPrice = paid_price
            db.commit()
            db.refresh(sub)
            return _subscription_out(db, sub, new_service)

    # Upgrade, or a same-tier billing-period change — applies immediately, prorated.
    if sub.StripeSubscriptionId:
        try:
            stripe_service.change_subscription_plan(sub.StripeSubscriptionId, new_price_id)
        except Exception:
            logger.exception("Stripe plan change failed for Subscription %s", sub.Id)
            raise HTTPException(502, "Failed to update billing with Stripe — please try again.")

    sub.ServiceId = new_service.Id
    sub.BillingPeriod = new_billing_period
    sub.PaidPrice = paid_price
    sub.PendingServiceId = None
    sub.PendingBillingPeriod = None
    db.commit()
    db.refresh(sub)

    return _subscription_out(db, sub, new_service)


@router.get("/service-instances", response_model=list[schemas.ServiceInstanceRead])
def list_service_instances(
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
    return [_service_instance_out(db, i) for i in instances]


@router.patch("/service-instances/{instance_id}/setup", response_model=schemas.ServiceInstanceRead)
def update_service_instance_setup(
    instance_id: int,
    body: schemas.ServiceInstanceSetup,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.setup_status is not None and body.setup_status not in _VALID_SETUP_STATUSES:
        raise HTTPException(400, "Invalid setup_status")

    company = resolve_account_company(db, current_user)
    instance = (
        db.query(models.ServiceInstance)
        .join(models.Subscription, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
        .filter(
            models.ServiceInstance.Id == instance_id,
            models.Subscription.CompanyId == company.Id,
        )
        .first()
    )
    if instance is None:
        raise HTTPException(404, "Service instance not found")

    if body.setup_status is not None:
        instance.SetupStatus = body.setup_status
    if body.configuration is not None:
        violation = _gated_tier_violation(db, instance, body.configuration)
        if violation:
            raise HTTPException(403, f"This requires the {violation} plan or higher.")
        instance.ConfigurationData = json.dumps(body.configuration)

    db.commit()
    db.refresh(instance)
    return _service_instance_out(db, instance)


@router.get("/invoices", response_model=list[schemas.InvoiceRead])
def list_invoices(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    if not company.StripeCustomerId:
        return []
    try:
        return stripe_service.list_invoices(company.StripeCustomerId)
    except Exception:
        logger.exception("Failed to list Stripe invoices for company %s", company.Id)
        return []
