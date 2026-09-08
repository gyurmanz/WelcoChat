# app/routers/billing.py
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas, stripe_service
from ..deps import get_db, get_current_user, resolve_account_company

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


@router.get("/countries", response_model=list[schemas.CountryRead])
def list_countries(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Country).order_by(models.Country.Name).all()


@router.get("/company", response_model=Optional[schemas.CompanyRead])
def get_company(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return resolve_account_company(db, current_user)


@router.put("/company", response_model=schemas.CompanyRead)
def upsert_company(
    req: schemas.CompanyUpsert,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    company = resolve_account_company(db, current_user)

    company.Name = req.name
    company.CountryId = req.country_id
    company.PostalCode = req.postal_code
    company.City = req.city
    company.AddressLine = req.address_line
    company.TaxNumber = req.tax_number

    db.commit()
    db.refresh(company)
    return company


@router.post("/portal-session", response_model=schemas.PortalSessionRead)
def create_portal_session(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    if not company.StripeCustomerId:
        raise HTTPException(400, "No billing account yet — start a subscription first")
    try:
        url = stripe_service.create_portal_session(
            company.StripeCustomerId, return_url=f"{FRONTEND_BASE_URL}/invoices"
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    return schemas.PortalSessionRead(url=url)


def _current_period_end(stripe_sub: dict):
    """Newer Stripe API versions moved current_period_end off the
    subscription object onto its first item; fall back to the old
    top-level field for older responses."""
    items = (stripe_sub.get("items") or {}).get("data") or []
    ts = stripe_sub.get("current_period_end")
    if ts is None and items:
        ts = items[0].get("current_period_end")
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None) if ts else None


def _sync_subscription_from_stripe(db: Session, stripe_sub) -> None:
    sub = (
        db.query(models.Subscription)
        .filter(models.Subscription.StripeSubscriptionId == stripe_sub["id"])
        .first()
    )
    if sub is None:
        return

    sub.Status = stripe_sub["status"]
    if stripe_sub.get("trial_end"):
        sub.TrialEndsAt = datetime.fromtimestamp(stripe_sub["trial_end"], tz=timezone.utc).replace(tzinfo=None)
    end = _current_period_end(stripe_sub)
    if end:
        sub.EndDate = end

    # A Subscription Schedule phase transition (a deferred downgrade taking
    # effect) changes the underlying Stripe subscription's price directly —
    # detect that here and mirror it into our own plan tracking, rather than
    # relying on any of our own timing.
    items = (stripe_sub.get("items") or {}).get("data") or []
    if items:
        price_id = (items[0].get("price") or {}).get("id")
        if price_id:
            service = (
                db.query(models.Service)
                .filter(or_(models.Service.StripePriceIdMonthly == price_id, models.Service.StripePriceIdAnnual == price_id))
                .first()
            )
            if service is not None and service.Id != sub.ServiceId:
                sub.ServiceId = service.Id
                sub.BillingPeriod = "annual" if service.StripePriceIdAnnual == price_id else "monthly"
                sub.PaidPrice = (
                    Decimal(str(round(float(service.AnnualPrice) * 12, 2)))
                    if sub.BillingPeriod == "annual" else Decimal(str(service.MonthlyPrice))
                )
                sub.PendingServiceId = None
                sub.PendingBillingPeriod = None

    db.commit()


def _handle_checkout_completed(db: Session, session: dict) -> None:
    stripe_sub_id = session.get("subscription")
    if not stripe_sub_id:
        return
    if db.query(models.Subscription).filter(models.Subscription.StripeSubscriptionId == stripe_sub_id).first():
        return  # already processed — Stripe may retry webhook delivery

    try:
        company_id = int(session["client_reference_id"])
        service_id = int(session["metadata"]["service_id"])
        billing_period = session["metadata"]["billing_period"]
        created_by_user_id = int(session["metadata"]["user_id"])
    except (KeyError, TypeError, ValueError):
        logger.error("checkout.session.completed missing expected fields (session=%s)", session.get("id"))
        return

    company = db.query(models.Company).filter(models.Company.Id == company_id).first()
    service = db.query(models.Service).filter(models.Service.Id == service_id).first()
    if company is None or service is None:
        logger.error(
            "checkout.session.completed: company or service not found (company_id=%s, service_id=%s)", company_id, service_id
        )
        return

    try:
        stripe_sub = stripe_service.retrieve_subscription(stripe_sub_id)
    except Exception:
        logger.exception("Failed to retrieve Stripe subscription %s after checkout", stripe_sub_id)
        return

    end = _current_period_end(stripe_sub)
    paid_price = (
        Decimal(str(round(float(service.AnnualPrice) * 12, 2)))
        if billing_period == "annual" else Decimal(str(service.MonthlyPrice))
    )

    sub = models.Subscription(
        CompanyId=company.Id,
        UserId=created_by_user_id,
        Type=service.ServiceKey,
        Status=stripe_sub["status"],
        ServiceId=service.Id,
        BillingPeriod=billing_period,
        PaidPrice=paid_price,
        StartDate=datetime.utcnow(),
        EndDate=end,
        TrialEndsAt=None,
        StripeSubscriptionId=stripe_sub_id,
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


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_service.construct_webhook_event(payload, sig_header)
    except Exception:
        logger.exception("Stripe webhook signature verification failed")
        raise HTTPException(400, "Invalid webhook signature")

    event_type = event["type"]
    obj = event["data"]["object"].to_dict()

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, obj)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        _sync_subscription_from_stripe(db, obj)
    elif event_type in ("invoice.paid", "invoice.payment_failed"):
        stripe_sub_id = obj.get("subscription")
        if stripe_sub_id:
            sub = (
                db.query(models.Subscription)
                .filter(models.Subscription.StripeSubscriptionId == stripe_sub_id)
                .first()
            )
            if sub is not None and event_type == "invoice.payment_failed":
                sub.Status = "past_due"
                db.commit()

    return {"status": "ok"}
