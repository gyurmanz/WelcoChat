# app/routers/contact.py
import os
import html

from fastapi import APIRouter, HTTPException

from .. import schemas
from ..email.service import send_email

router = APIRouter()

# Hova menjenek a kaptila.com landing-oldal demo-kerelmei (env-bol felulirhato).
CONTACT_TO = os.getenv("CONTACT_TO", "notification@kaptila.com")


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
