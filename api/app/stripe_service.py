# app/stripe_service.py
"""Stripe billing integration. Every function raises RuntimeError if
STRIPE_SECRET_KEY is unset — callers catch that and no-op around it, so the
app works exactly as it did before Stripe was configured until a key lands.
"""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from . import models

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


def _client():
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe is not yet configured")

    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def get_or_create_customer(db: Session, company: models.Company, contact_email: str, contact_name: str) -> str:
    """One Stripe customer per Company — its identity shouldn't shift
    depending on which team member happens to click checkout, so the
    contact email/name passed in should be the company's designated owner,
    not necessarily whoever is making this particular request."""
    if company.StripeCustomerId:
        return company.StripeCustomerId

    stripe = _client()
    customer = stripe.Customer.create(email=contact_email, name=company.Name or contact_name)
    company.StripeCustomerId = customer.id
    db.commit()
    return customer.id


def resolve_promo_code(code: str) -> str:
    """Looks up an active Stripe Promotion Code by its customer-facing code
    (e.g. "PRODUCTHUNT") and returns its id. Raises ValueError if the code
    doesn't exist or isn't active — callers should surface that to the user
    rather than silently dropping the discount."""
    stripe = _client()
    matches = stripe.PromotionCode.list(code=code.strip(), active=True, limit=1)
    if not matches.data:
        raise ValueError("Invalid or expired promo code")
    return matches.data[0].id


def create_trial_subscription(
    db: Session,
    company: models.Company,
    contact_email: str,
    contact_name: str,
    service: models.Service,
    billing_period: str,
    trial_end: datetime,
    promotion_code_id: str | None = None,
) -> str:
    stripe = _client()

    price_id = service.StripePriceIdAnnual if billing_period == "annual" else service.StripePriceIdMonthly
    if not price_id:
        raise RuntimeError(f"No Stripe price configured for service {service.ServiceKey}/{service.Tier}/{billing_period}")

    customer_id = get_or_create_customer(db, company, contact_email, contact_name)

    trial_end_ts = int(trial_end.replace(tzinfo=timezone.utc).timestamp())

    kwargs = {}
    if promotion_code_id:
        # Attached now so it's already on the subscription once the trial ends
        # and Stripe starts actually billing it — nothing to do at conversion time.
        kwargs["discounts"] = [{"promotion_code": promotion_code_id}]

    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        trial_end=trial_end_ts,
        trial_settings={"end_behavior": {"missing_payment_method": "pause"}},
        payment_settings={"save_default_payment_method": "on_subscription"},
        **kwargs,
    )
    return subscription.id


def change_subscription_plan(stripe_sub_id: str, new_price_id: str) -> None:
    stripe = _client()
    current = stripe.Subscription.retrieve(stripe_sub_id)
    item_id = current["items"]["data"][0]["id"]
    stripe.Subscription.modify(
        stripe_sub_id,
        items=[{"id": item_id, "price": new_price_id}],
        proration_behavior="create_prorations",
    )


def schedule_downgrade(stripe_sub_id: str, new_price_id: str) -> None:
    """Keeps the current price billing until the current period ends, then
    switches to new_price_id — Stripe handles the timing/billing itself, so
    there's no race with our own webhooks about exactly when to apply it."""
    stripe = _client()

    # Any subscription that ever went through create_trial_subscription carries
    # trial_settings.end_behavior.missing_payment_method="pause" *permanently*
    # (not just while actually trialing) — Stripe refuses to create a schedule
    # from such a subscription at all, even long after the trial has ended and
    # it's a normal paying subscription. Harmless to clear here: by this point
    # the subscription is guaranteed not to be trialing (callers only reach
    # this once the trial is over), so the setting can no longer do anything.
    current = stripe.Subscription.retrieve(stripe_sub_id).to_dict()
    if (current.get("trial_settings") or {}).get("end_behavior", {}).get("missing_payment_method") == "pause":
        stripe.Subscription.modify(
            stripe_sub_id, trial_settings={"end_behavior": {"missing_payment_method": "create_invoice"}}
        )

    schedule = stripe.SubscriptionSchedule.create(from_subscription=stripe_sub_id)
    current_phase = schedule["phases"][0]
    stripe.SubscriptionSchedule.modify(
        schedule.id,
        end_behavior="release",
        phases=[
            {
                "items": [{"price": i["price"], "quantity": i["quantity"]} for i in current_phase["items"]],
                "start_date": current_phase["start_date"],
                "end_date": current_phase["end_date"],
            },
            {"items": [{"price": new_price_id, "quantity": 1}]},
        ],
    )


def cancel_scheduled_downgrade(stripe_sub_id: str) -> None:
    """Releases the subscription from its schedule, cancelling a pending
    downgrade — it just keeps billing the current (phase 1) price forever."""
    stripe = _client()
    sub = stripe.Subscription.retrieve(stripe_sub_id).to_dict()
    schedule_id = sub.get("schedule")
    if schedule_id:
        stripe.SubscriptionSchedule.release(schedule_id)


def create_checkout_session(
    customer_id: str, price_id: str, client_reference_id: str, metadata: dict, success_url: str, cancel_url: str,
) -> str:
    stripe = _client()
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=client_reference_id,
        metadata=metadata,
        success_url=success_url,
        cancel_url=cancel_url,
        # Lets Stripe show its own "Add promotion code" field on the hosted
        # checkout page — no separate UI needed on our side for this path.
        allow_promotion_codes=True,
    )
    return session.url


def retrieve_subscription(stripe_sub_id: str) -> dict:
    """Returns a plain dict (not a StripeObject) — StripeObject doesn't
    support .get(), which every caller here relies on."""
    stripe = _client()
    return stripe.Subscription.retrieve(stripe_sub_id).to_dict()


def create_portal_session(customer_id: str, return_url: str) -> str:
    stripe = _client()
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def list_invoices(customer_id: str) -> list[dict]:
    stripe = _client()
    invoices = stripe.Invoice.list(customer=customer_id, limit=24)

    out = []
    for inv in invoices.auto_paging_iter():
        amount = inv.amount_paid if inv.amount_paid else inv.amount_due
        out.append({
            "id": inv.id,
            "number": inv.number,
            "issued_date": datetime.fromtimestamp(inv.created, tz=timezone.utc) if inv.created else None,
            "period": None,
            "amount": (amount / 100) if amount is not None else None,
            "currency": inv.currency,
            "status": inv.status,
            "pdf_url": inv.invoice_pdf,
        })
    return out


def construct_webhook_event(payload: bytes, sig_header: str):
    stripe = _client()
    if not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("Stripe webhook secret is not yet configured")
    return stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
