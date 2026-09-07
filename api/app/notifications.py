# app/notifications.py
"""Outbound Slack/Teams webhook notifications — one-way only, no OAuth, no
read-back. A customer pastes an Incoming Webhook URL (Slack) or a Workflows
webhook URL (Teams) into their instance settings; we just POST to it."""
import json
import logging
from datetime import datetime

import requests
from sqlalchemy.orm import Session

from . import models
from .deps import instance_has_tier

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5


def _slack_payload(message: str) -> dict:
    return {"text": message}


def _teams_payload(message: str) -> dict:
    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [{"type": "TextBlock", "text": message, "wrap": True}],
            },
        }],
    }


def _generic_payload(message: str, event: str | None, data: dict | None) -> dict:
    return {
        "event": event or "notification",
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **(data or {}),
    }


def _build_payload(channel_type: str, message: str, event: str | None, data: dict | None) -> dict:
    if channel_type == "slack":
        return _slack_payload(message)
    if channel_type == "teams":
        return _teams_payload(message)
    return _generic_payload(message, event, data)


def send_notification(
    channel_type: str, webhook_url: str, message: str, event: str | None = None, data: dict | None = None
) -> None:
    """Raises on failure — used by the test-message endpoint, where the caller
    wants to know whether it actually worked."""
    payload = _build_payload(channel_type, message, event, data)
    resp = requests.post(webhook_url, json=payload, timeout=_TIMEOUT_SECONDS)
    resp.raise_for_status()


def notify_instance(
    db: Session, instance: models.ServiceInstance, message: str, event: str | None = None, data: dict | None = None
) -> None:
    """Best-effort — never raises. No-op if the instance has no channel configured
    or if its plan tier no longer includes notifications (e.g. downgraded after
    a Business+ channel was configured)."""
    config = json.loads(instance.ConfigurationData) if instance.ConfigurationData else {}
    channel_type = config.get("notification_channel_type")
    webhook_url = config.get("notification_webhook_url")
    if channel_type not in ("slack", "teams", "generic") or not webhook_url:
        return
    if not instance_has_tier(db, instance, "Business"):
        return
    try:
        send_notification(channel_type, webhook_url, message, event=event, data=data)
    except Exception:
        logger.warning("Notification delivery failed for ServiceInstance %s", instance.Id, exc_info=True)
