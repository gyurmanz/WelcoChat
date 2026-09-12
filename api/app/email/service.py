# app/email/service.py
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from string import Template
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@example.com")
SUBJECT_EMAIL_VERIFICATION = os.getenv("SUBJECT_EMAIL_VERIFICATION", "Email Verification")
SUBJECT_PASSWORD_RESET = os.getenv("SUBJECT_PASSWORD_RESET", "Password Reset Request") 

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def render_template(template_name: str, **context) -> str:
    """HTML template kitöltése string.Template segítségével."""
    template_path = TEMPLATE_DIR / template_name
    raw_html = template_path.read_text(encoding="utf-8")

    tmpl = Template(raw_html)
    rendered = tmpl.safe_substitute(**context)  # <-- EZ A LÉNYEG

    return rendered


def send_email(subject: str, email_to: str, html_body: str, text_body: str = None, reply_to: str = None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = email_to
    # Support mail is only useful if hitting reply reaches the customer rather
    # than our own From address.
    if reply_to:
        msg["Reply-To"] = reply_to

    if not text_body:
        text_body = "HTML email only."

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        if SMTP_USE_TLS:
            server.starttls()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def send_registration_email(email_to: str, token: str, display_name: str):
    confirm_url = f"{FRONTEND_BASE_URL}/verify-email?token={token}"

    html_body = render_template(
        "registration_confirm.html",
        confirm_url=confirm_url,
        display_name=display_name,
    )

    text_body = f"Click to confirm your registration: {confirm_url}"

    send_email(
        subject=SUBJECT_EMAIL_VERIFICATION,
        email_to=email_to,
        html_body=html_body,
        text_body=text_body,
    )


def send_password_reset_email(email_to: str, token: str, display_name: str = None):
    reset_url = (
        f"{FRONTEND_BASE_URL}/reset-password"
        f"?token={token}&email={quote(email_to)}"
    )

    html_body = render_template(
        "password_reset.html",
        reset_url=reset_url,
        display_name=display_name or "",
    )

    text_body = f"Reset your password using this link: {reset_url}"

    send_email(
        subject=SUBJECT_PASSWORD_RESET,
        email_to=email_to,
        html_body=html_body,
        text_body=text_body,
    )


def send_live_handoff_email(email_to: str):
    live_chat_url = f"{FRONTEND_BASE_URL}/live-chat"

    html_body = render_template("live_handoff.html", live_chat_url=live_chat_url)
    text_body = f"A visitor needs help on your Kaptila Welco widget. Open Live Chat: {live_chat_url}"

    send_email(
        subject="A visitor needs help — Kaptila Welco",
        email_to=email_to,
        html_body=html_body,
        text_body=text_body,
    )


def send_trial_ending_email(email_to: str, display_name: str, days_left: int, trial_end_date: str):
    """Sent by the daily maintenance job a few days before a trial lapses. Without
    it a trial just stops answering on day 14 with no warning, which is the
    easiest possible way to lose a customer who meant to pay."""
    billing_url = f"{FRONTEND_BASE_URL}/invoices"
    when = "tomorrow" if days_left <= 1 else f"in {days_left} days"

    html_body = render_template(
        "trial_ending.html",
        display_name=display_name or "there",
        when=when,
        trial_end_date=trial_end_date,
        billing_url=billing_url,
    )
    text_body = (
        f"Your WelcoChat trial ends {when} ({trial_end_date}). "
        f"Add a payment method to keep your agent running: {billing_url}"
    )

    send_email(
        subject=f"Your WelcoChat trial ends {when}",
        email_to=email_to,
        html_body=html_body,
        text_body=text_body,
    )


def send_email_change_email(email_to: str, token: str, display_name: str = None):
    confirm_url = f"{FRONTEND_BASE_URL}/confirm-email-change?token={token}"

    html_body = render_template(
        "email_change_confirm.html",
        confirm_url=confirm_url,
        display_name=display_name or "",
    )

    text_body = f"Confirm your new email address using this link: {confirm_url}"

    send_email(
        subject="Confirm your new email address",
        email_to=email_to,
        html_body=html_body,
        text_body=text_body,
    )
