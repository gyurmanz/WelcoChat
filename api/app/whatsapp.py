# app/whatsapp.py
"""Twilio WhatsApp integration — the customer brings their own Twilio account
and WhatsApp sender (same "customer does their own platform setup" pattern as
the Slack/Teams notification webhooks). No Twilio SDK — plain HTTP, matching
the rest of the app's minimal-dependency style."""
import base64
import hashlib
import hmac
from xml.sax.saxutils import escape

import requests

_TIMEOUT_SECONDS = 10


def verify_signature(auth_token: str, url: str, params: dict, signature: str) -> bool:
    """Twilio signs a request as base64(HMAC-SHA1(url + sorted "key"+"value" pairs, auth_token)).
    `url` must be the exact public URL Twilio was configured to call — built from a
    known constant, never from the incoming request, since a proxy can misreport
    the scheme and would silently break verification."""
    if not signature:
        return False
    data = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    computed = base64.b64encode(hmac.new(auth_token.encode(), data.encode(), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(computed, signature)


def send_whatsapp_message(account_sid: str, auth_token: str, from_number: str, to_number: str, body: str) -> None:
    """Raises on failure — used for portal-initiated (human) replies, where the
    caller needs to know delivery actually succeeded."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    resp = requests.post(
        url,
        data={"From": f"whatsapp:{from_number}", "To": f"whatsapp:{to_number}", "Body": body},
        auth=(account_sid, auth_token),
        timeout=_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()


def twiml_message(text: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(text)}</Message></Response>'


def empty_twiml() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
