# app/routers/welco.py
import json
import logging
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas
from ..welco_quota import (
    QUOTA_GRACE, conversation_limit_for_instance, conversations_this_month,
    notify_quota_reached, session_already_counted,
)
from ..deps import get_db, get_current_user, resolve_account_company, instance_has_tier, instance_subscription_active
from ..database import SessionLocal
from ..email.service import send_email, send_live_handoff_email, FRONTEND_BASE_URL
from ..welco_crawler import crawl_site
from .. import welco_engine
from .. import welco_documents
from .. import notifications
from .. import push_service
from .. import whatsapp

logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter()

WIDGET_BASE_URL = os.getenv("API_BASE_URL", "https://welcochat.com/api")

LOGO_UPLOAD_DIR = Path(__file__).resolve().parent.parent / "static" / "uploads" / "logos"
MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_CONTENT_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}

CHAT_IMAGE_MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_CHAT_IMAGE_BASE64_CHARS = 7_000_000  # ~5MB raw (base64 is ~4/3 the raw size)

_RATE_LIMIT_MAX = 30
_RATE_LIMIT_WINDOW_SECONDS = 3600
_rate_limit_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def _rate_limited(client_ip: str, public_id: str) -> bool:
    key = (client_ip, public_id)
    now = time.monotonic()
    hits = _rate_limit_hits[key]
    while hits and now - hits[0] > _RATE_LIMIT_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= _RATE_LIMIT_MAX:
        return True
    hits.append(now)
    return False


def _get_owned_instance(db: Session, instance_id: int, company_id: int) -> models.ServiceInstance:
    instance = (
        db.query(models.ServiceInstance)
        .join(models.Subscription, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
        .filter(
            models.ServiceInstance.Id == instance_id,
            models.Subscription.CompanyId == company_id,
        )
        .first()
    )
    if instance is None:
        raise HTTPException(404, "Service instance not found")
    if instance.ServiceKey != "welco":
        raise HTTPException(400, "This endpoint is for WelcoChat instances only")
    return instance


def _embed_snippet(public_id: str) -> str:
    return (
        f'<script src="{WIDGET_BASE_URL}/static/welco-widget.js" '
        f'data-agent="{public_id}" defer></script>'
    )


def _whatsapp_webhook_url(public_id: str) -> str:
    return f"{WIDGET_BASE_URL}/widget/{public_id}/whatsapp"


def _build_kb_content(db: Session, kb: models.WelcoKnowledgeBase, config: dict) -> str:
    docs = (
        db.query(models.WelcoDocument)
        .filter(models.WelcoDocument.ServiceInstanceId == kb.ServiceInstanceId)
        .all()
    )
    doc_chars = 0
    doc_chunks = []
    for d in docs:
        if not d.ExtractedText:
            continue
        remaining = welco_documents.MAX_DOC_CHARS_TOTAL - doc_chars
        if remaining <= 0:
            break
        piece = f"\n\n=== Uploaded document: {d.FileName} ===\n{d.ExtractedText[:remaining]}"
        doc_chunks.append(piece)
        doc_chars += len(piece)

    notes = (config.get("additional_docs_note") or "").strip()
    notes_chunk = f"\n\n=== Additional notes ===\n{notes}" if notes else ""

    return (kb.Content or "") + "".join(doc_chunks) + notes_chunk


def _run_crawl(kb_id: int, instance_id: int, website_url: str) -> None:
    db = SessionLocal()
    try:
        try:
            content, page_count = crawl_site(website_url)
            kb = db.query(models.WelcoKnowledgeBase).filter(models.WelcoKnowledgeBase.Id == kb_id).first()
            instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == instance_id).first()
            if kb is None or instance is None:
                return
            kb.Content = content
            kb.PageCount = page_count
            kb.Status = "ready"
            kb.ErrorMessage = None
            kb.CrawledAt = datetime.utcnow()
            instance.SetupStatus = "running"
            db.commit()
        except Exception as exc:  # noqa: BLE001 — crawl failures must not crash the background task
            db.rollback()
            kb = db.query(models.WelcoKnowledgeBase).filter(models.WelcoKnowledgeBase.Id == kb_id).first()
            instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == instance_id).first()
            if kb is not None:
                kb.Status = "error"
                kb.ErrorMessage = str(exc)[:500]
            if instance is not None:
                instance.SetupStatus = "error"
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Authenticated (portal) endpoints
# ---------------------------------------------------------------------------

@router.post("/instances/{instance_id}/activate", response_model=schemas.WelcoStatusRead)
def activate_welco(
    instance_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)
    config = json.loads(instance.ConfigurationData) if instance.ConfigurationData else {}
    website_url = config.get("website_url")
    if not website_url:
        raise HTTPException(400, "Set a website URL before activating")

    kb = (
        db.query(models.WelcoKnowledgeBase)
        .filter(models.WelcoKnowledgeBase.ServiceInstanceId == instance.Id)
        .first()
    )
    if kb is None:
        kb = models.WelcoKnowledgeBase(
            ServiceInstanceId=instance.Id,
            PublicId=str(uuid.uuid4()),
            Status="crawling",
            SourceUrl=website_url,
        )
        db.add(kb)
    else:
        kb.Status = "crawling"
        kb.SourceUrl = website_url
        kb.ErrorMessage = None

    instance.SetupStatus = "pending_review"
    db.commit()
    db.refresh(kb)

    background_tasks.add_task(_run_crawl, kb.Id, instance.Id, website_url)

    return schemas.WelcoStatusRead(
        status=kb.Status, page_count=kb.PageCount, error_message=kb.ErrorMessage,
        whatsapp_webhook_url=_whatsapp_webhook_url(kb.PublicId),
    )


@router.get("/instances/{instance_id}/status", response_model=schemas.WelcoStatusRead)
def welco_status(
    instance_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)
    kb = (
        db.query(models.WelcoKnowledgeBase)
        .filter(models.WelcoKnowledgeBase.ServiceInstanceId == instance.Id)
        .first()
    )
    if kb is None:
        return schemas.WelcoStatusRead(status="pending")

    embed_snippet = _embed_snippet(kb.PublicId) if kb.Status == "ready" else None
    return schemas.WelcoStatusRead(
        status=kb.Status,
        page_count=kb.PageCount,
        error_message=kb.ErrorMessage,
        embed_snippet=embed_snippet,
        whatsapp_webhook_url=_whatsapp_webhook_url(kb.PublicId),
    )


@router.post("/instances/{instance_id}/test-notification")
def test_notification(
    instance_id: int,
    body: schemas.NotificationTestRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)
    if not instance_has_tier(db, instance, "Business"):
        raise HTTPException(403, "Slack/Teams/webhook notifications are available on the Business plan and up.")
    if body.channel_type not in ("slack", "teams", "generic"):
        raise HTTPException(400, "channel_type must be 'slack', 'teams' or 'generic'")
    try:
        notifications.send_notification(
            body.channel_type, body.webhook_url, "This is a test notification from WelcoChat.",
            event="test", data={"instance_id": instance_id},
        )
    except Exception:
        raise HTTPException(400, "Could not reach that webhook URL — please double-check it.")
    return {"status": "ok"}


@router.post("/instances/{instance_id}/logo", response_model=schemas.WelcoLogoUploadResult)
def upload_logo(
    instance_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)
    if not instance_has_tier(db, instance, "Business"):
        raise HTTPException(403, "Custom widget branding is available on the Business plan and up.")

    ext = LOGO_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(400, "Logo must be a PNG, JPEG, WebP or SVG image.")

    content = file.file.read()
    if len(content) > MAX_LOGO_BYTES:
        raise HTTPException(400, "Logo file is too large (max 2 MB).")

    LOGO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for existing in LOGO_UPLOAD_DIR.glob(f"logo_{instance_id}.*"):
        existing.unlink()
    file_path = LOGO_UPLOAD_DIR / f"logo_{instance_id}.{ext}"
    file_path.write_bytes(content)

    config = json.loads(instance.ConfigurationData) if instance.ConfigurationData else {}
    logo_url = f"{WIDGET_BASE_URL}/static/uploads/logos/logo_{instance_id}.{ext}?v={int(time.time())}"
    config["widget_logo_url"] = logo_url
    instance.ConfigurationData = json.dumps(config)
    db.commit()

    return schemas.WelcoLogoUploadResult(logo_url=logo_url)


@router.delete("/instances/{instance_id}/logo", status_code=204)
def delete_logo(
    instance_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)
    if LOGO_UPLOAD_DIR.exists():
        for existing in LOGO_UPLOAD_DIR.glob(f"logo_{instance_id}.*"):
            existing.unlink()
    config = json.loads(instance.ConfigurationData) if instance.ConfigurationData else {}
    config.pop("widget_logo_url", None)
    instance.ConfigurationData = json.dumps(config)
    db.commit()


def _document_out(doc: models.WelcoDocument) -> schemas.WelcoDocumentRead:
    return schemas.WelcoDocumentRead(
        id=doc.Id, file_name=doc.FileName, char_count=doc.CharCount, uploaded_at=doc.UploadedAt
    )


@router.get("/leads", response_model=list[schemas.WelcoLeadRead])
def list_leads(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every lead the company's agents have captured, newest first. The widget
    writes these; until this existed they were write-only and the customer had
    no way to reach the contact details they were paying to collect."""
    company = resolve_account_company(db, current_user)
    rows = (
        db.query(models.WelcoLead, models.ServiceInstance.ServiceName)
        .join(models.ServiceInstance, models.WelcoLead.ServiceInstanceId == models.ServiceInstance.Id)
        .join(models.Subscription, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
        .filter(models.Subscription.CompanyId == company.Id)
        .order_by(models.WelcoLead.Created.desc())
        .all()
    )
    return [
        schemas.WelcoLeadRead(
            id=lead.Id,
            instance_id=lead.ServiceInstanceId,
            instance_name=instance_name,
            name=lead.VisitorName,
            email=lead.VisitorEmail,
            whatsapp=lead.VisitorWhatsapp,
            message=lead.Message,
            created=lead.Created,
        )
        for lead, instance_name in rows
    ]


@router.get("/instances/{instance_id}/documents", response_model=list[schemas.WelcoDocumentRead])
def list_documents(
    instance_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)
    docs = (
        db.query(models.WelcoDocument)
        .filter(models.WelcoDocument.ServiceInstanceId == instance.Id)
        .order_by(models.WelcoDocument.UploadedAt.asc())
        .all()
    )
    return [_document_out(d) for d in docs]


@router.post("/instances/{instance_id}/documents", response_model=list[schemas.WelcoDocumentUploadResult])
def upload_documents(
    instance_id: int,
    files: list[UploadFile] = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)

    existing_count = (
        db.query(models.WelcoDocument)
        .filter(models.WelcoDocument.ServiceInstanceId == instance.Id)
        .count()
    )

    results: list[schemas.WelcoDocumentUploadResult] = []
    for f in files:
        if existing_count + len(results) >= welco_documents.MAX_FILES_PER_INSTANCE:
            results.append(schemas.WelcoDocumentUploadResult(
                file_name=f.filename or "unknown", error="Document limit reached (max 20 per agent)"
            ))
            continue

        content = f.file.read()
        if len(content) > welco_documents.MAX_FILE_BYTES:
            results.append(schemas.WelcoDocumentUploadResult(
                file_name=f.filename or "unknown", error="File too large (max 10 MB)"
            ))
            continue

        try:
            text = welco_documents.extract_text(f.filename or "", content)
        except ValueError as exc:
            results.append(schemas.WelcoDocumentUploadResult(file_name=f.filename or "unknown", error=str(exc)))
            continue
        except Exception:
            results.append(schemas.WelcoDocumentUploadResult(
                file_name=f.filename or "unknown", error="Could not read this file"
            ))
            continue

        doc = models.WelcoDocument(
            ServiceInstanceId=instance.Id,
            FileName=f.filename or "unknown",
            ExtractedText=text,
            CharCount=len(text),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        results.append(schemas.WelcoDocumentUploadResult(file_name=doc.FileName, id=doc.Id, char_count=doc.CharCount))

    return results


@router.delete("/instances/{instance_id}/documents/{doc_id}", status_code=204)
def delete_document(
    instance_id: int,
    doc_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = _get_owned_instance(db, instance_id, resolve_account_company(db, current_user).Id)
    doc = (
        db.query(models.WelcoDocument)
        .filter(models.WelcoDocument.Id == doc_id, models.WelcoDocument.ServiceInstanceId == instance.Id)
        .first()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()


# ---------------------------------------------------------------------------
# Public (widget) endpoints — no auth, CORS opened for /widget/* in main.py
# ---------------------------------------------------------------------------

widget_router = APIRouter()


def _get_ready_kb(db: Session, public_id: str) -> models.WelcoKnowledgeBase:
    kb = (
        db.query(models.WelcoKnowledgeBase)
        .filter(models.WelcoKnowledgeBase.PublicId == public_id, models.WelcoKnowledgeBase.Status == "ready")
        .first()
    )
    if kb is None:
        raise HTTPException(404, "Agent not found")

    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
    if instance is None or not instance_subscription_active(db, instance):
        raise HTTPException(402, "This agent is currently paused.")

    return kb


@widget_router.get("/{public_id}/config", response_model=schemas.WelcoWidgetConfig)
def widget_config(public_id: str, db: Session = Depends(get_db)):
    kb = _get_ready_kb(db, public_id)
    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
    config = json.loads(instance.ConfigurationData) if instance and instance.ConfigurationData else {}

    theme = config.get("widget_theme")
    if theme not in ("light", "dark", "custom"):
        theme = "light"

    if theme == "custom":
        widget_color = config.get("widget_color") or "#2563eb"
        widget_bg_color = config.get("widget_bg_color") or "#ffffff"
    else:
        # Light/dark presets use a fixed accent — customers only choose colors in "custom".
        widget_color = "#2563eb"
        widget_bg_color = ""

    has_business = instance is not None and instance_has_tier(db, instance, "Business")
    has_enterprise = instance is not None and instance_has_tier(db, instance, "Enterprise")

    return schemas.WelcoWidgetConfig(
        widget_name=config.get("widget_name") or "Welco Assistant",
        widget_color=widget_color,
        widget_bg_color=widget_bg_color,
        widget_theme=theme,
        greeting_message=config.get("greeting_message") or "Hi! How can I help you today?",
        widget_logo_url=config.get("widget_logo_url") if has_business else None,
        widget_position=(config.get("widget_position") or "bottom-right") if has_business else "bottom-right",
        widget_custom_css=config.get("widget_custom_css") if has_enterprise else None,
        image_upload_enabled=has_business,
        widget_language=config.get("widget_language") or "",
    )


@widget_router.post("/{public_id}/message", response_model=schemas.WelcoMessageResponse)
def widget_message(public_id: str, body: schemas.WelcoMessageRequest, request: Request, db: Session = Depends(get_db)):
    kb = _get_ready_kb(db, public_id)

    if not body.message.strip() and not body.image_data:
        raise HTTPException(400, "Provide a message or an image")

    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip, public_id):
        raise HTTPException(429, "Too many messages, please try again later")

    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
    config = json.loads(instance.ConfigurationData) if instance and instance.ConfigurationData else {}
    widget_name = config.get("widget_name") or "Welco Assistant"

    if body.image_data:
        if instance is None or not instance_has_tier(db, instance, "Business"):
            raise HTTPException(403, "Image attachments are available on the Business plan and up.")
        if body.image_media_type not in CHAT_IMAGE_MEDIA_TYPES:
            raise HTTPException(400, "Image must be a PNG, JPEG, WebP or GIF.")
        if len(body.image_data) > MAX_CHAT_IMAGE_BASE64_CHARS:
            raise HTTPException(400, "Image is too large (max 5 MB).")

    limit = conversation_limit_for_instance(db, instance) if instance else None
    if limit:
        used = conversations_this_month(db, kb.ServiceInstanceId)
        if used >= limit and instance is not None:
            notify_quota_reached(db, instance, used, limit)
        # Only new conversations are turned away — one already counted this
        # month runs to its end.
        if used >= int(limit * QUOTA_GRACE) and not session_already_counted(db, kb.ServiceInstanceId, body.session_id):
            return schemas.WelcoMessageResponse(
                reply="I can't answer right now, but I can put you in touch with the team — they'll get back to you.",
                handoff=True,
            )

    kb_content = _build_kb_content(db, kb, config)

    try:
        reply, handoff = welco_engine.answer(
            kb_content=kb_content,
            history=[h.model_dump() for h in body.history],
            message=body.message,
            widget_name=widget_name,
            image_data=body.image_data,
            image_media_type=body.image_media_type,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))

    db.add(models.WelcoInteraction(
        ServiceInstanceId=kb.ServiceInstanceId, Handoff=handoff, SessionId=body.session_id or None,
    ))
    db.commit()

    return schemas.WelcoMessageResponse(reply=reply, handoff=handoff)


def _notify_new_lead(db: Session, instance: models.ServiceInstance, body: schemas.WelcoLeadRequest) -> None:
    """Emails the captured contact details to whoever the customer set as the
    notification recipient. Best-effort: a mail failure must never turn into a
    failed lead capture for the visitor."""
    if instance is None:
        return
    contact_lines = []
    if body.name:
        contact_lines.append(f"<li><strong>Name:</strong> {body.name}</li>")
    if body.email:
        contact_lines.append(f"<li><strong>Email:</strong> {body.email}</li>")
    if body.whatsapp:
        contact_lines.append(f"<li><strong>WhatsApp:</strong> {body.whatsapp}</li>")
    if body.message:
        contact_lines.append(f"<li><strong>Message:</strong> {body.message}</li>")

    try:
        recipient = _instance_notification_email(db, instance.Id)
        if recipient:
            send_email(
                subject=f"New lead from {instance.ServiceName}",
                email_to=recipient,
                html_body=(
                    "<p>Your WelcoChat agent captured a new lead:</p>"
                    f"<ul>{''.join(contact_lines)}</ul>"
                    f'<p><a href="{FRONTEND_BASE_URL}/leads">See all leads in the portal</a></p>'
                ),
            )
    except Exception:
        logger.exception("Failed to email new lead for ServiceInstance %s", instance.Id)

    notifications.notify_instance(
        db, instance,
        message=f"New lead from {instance.ServiceName}: " + ", ".join(
            v for v in (body.name, body.email, body.whatsapp) if v
        ),
        event="lead",
    )


def _instance_notification_email(db: Session, service_instance_id: int) -> str | None:
    """The handoff notification recipient is a per-instance setting (not the
    account's own email) — empty/unset means the customer opted out of email
    notifications entirely (they may still have Slack/Teams/webhook configured)."""
    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == service_instance_id).first()
    if instance is None or not instance.ConfigurationData:
        return None
    config = json.loads(instance.ConfigurationData)
    email = (config.get("notification_email") or "").strip()
    return email or None


def _conv_message_out(m: models.WelcoConversationMessage) -> schemas.WelcoConvMessageRead:
    return schemas.WelcoConvMessageRead(
        id=m.Id, sender=m.Sender, sender_name=m.SenderName, content=m.Content, created=m.Created,
    )


def _notify_handoff(
    db: Session, instance: models.ServiceInstance | None, service_instance_id: int, conversation_id: int, widget_name: str
) -> None:
    """Shared by the widget's create_conversation and the WhatsApp webhook —
    both need the exact same email + Slack/Teams/webhook notification on handoff."""
    live_chat_message = f"A visitor needs help on {widget_name} — open Live Chat: {FRONTEND_BASE_URL}/live-chat"

    notification_email = _instance_notification_email(db, service_instance_id)
    if notification_email:
        try:
            send_live_handoff_email(notification_email)
        except Exception:
            pass  # best-effort — a notification failure must not block the handoff itself

    if instance is not None:
        notifications.notify_instance(
            db, instance, live_chat_message,
            event="welco_handoff",
            data={
                "instance_id": service_instance_id,
                "conversation_id": conversation_id,
                "live_chat_url": f"{FRONTEND_BASE_URL}/live-chat",
            },
        )

        company_id = (
            db.query(models.Subscription.CompanyId)
            .join(models.ServiceInstance, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
            .filter(models.ServiceInstance.Id == instance.Id)
            .scalar()
        )
        if company_id is not None:
            try:
                push_service.notify_company_users(
                    db, company_id,
                    title=f"{widget_name} needs you",
                    body="A visitor needs a human — open Live Chat to reply.",
                    url="/portal/live-chat",
                )
            except Exception:
                logger.exception("Push notification failed for handoff on instance %s", service_instance_id)


@widget_router.post("/{public_id}/conversations", response_model=schemas.WelcoConversationCreateResponse, status_code=201)
def create_conversation(public_id: str, body: schemas.WelcoConversationCreate, request: Request, db: Session = Depends(get_db)):
    """Called by the widget the moment a handoff happens — creates a live,
    portal-visible conversation before falling back to the async email/WhatsApp
    contact form (that fallback only kicks in client-side if nobody replies in time)."""
    kb = _get_ready_kb(db, public_id)

    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip, public_id):
        raise HTTPException(429, "Too many messages, please try again later")

    conversation = models.WelcoConversation(
        ServiceInstanceId=kb.ServiceInstanceId, Status="waiting", Token=secrets.token_urlsafe(32),
    )
    db.add(conversation)
    db.flush()

    last_message_id = 0
    for h in body.history:
        sender = "visitor" if h.role == "user" else "agent"
        msg = models.WelcoConversationMessage(ConversationId=conversation.Id, Sender=sender, Content=h.content)
        db.add(msg)
        db.flush()
        last_message_id = msg.Id

    db.commit()

    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
    config = json.loads(instance.ConfigurationData) if instance and instance.ConfigurationData else {}
    widget_name = config.get("widget_name") or "Welco Assistant"
    _notify_handoff(db, instance, kb.ServiceInstanceId, conversation.Id, widget_name)

    return schemas.WelcoConversationCreateResponse(
        conversation_id=conversation.Id,
        conversation_token=conversation.Token,
        last_message_id=last_message_id,
    )


def _get_conversation_for_public_id(
    db: Session, public_id: str, conversation_id: int, token: str
) -> models.WelcoConversation:
    """Visitor-facing lookup. The Id alone is a sequential integer any visitor
    can guess, so the caller must also present the token handed out when the
    conversation was created — otherwise this is an open read/write door onto
    every other visitor's thread on the same widget."""
    kb = _get_ready_kb(db, public_id)
    conversation = (
        db.query(models.WelcoConversation)
        .filter(
            models.WelcoConversation.Id == conversation_id,
            models.WelcoConversation.ServiceInstanceId == kb.ServiceInstanceId,
        )
        .first()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    # Fail closed: a conversation with no token (only possible for rows created
    # before tokens existed, or the server-side WhatsApp path) is not reachable
    # from the widget at all.
    if not conversation.Token or not secrets.compare_digest(conversation.Token, token or ""):
        raise HTTPException(404, "Conversation not found")
    return conversation


@widget_router.get("/{public_id}/conversations/{conversation_id}", response_model=schemas.WelcoConversationFullResponse)
def get_full_conversation(public_id: str, conversation_id: int, token: str = "", db: Session = Depends(get_db)):
    """Lets the widget rebuild the whole visible thread after a page reload —
    unlike poll_conversation below (which only returns new human replies), this
    returns every message (visitor/agent/human) since the server-stored
    conversation is the single source of truth once a handoff has happened."""
    conversation = _get_conversation_for_public_id(db, public_id, conversation_id, token)
    messages = (
        db.query(models.WelcoConversationMessage)
        .filter(models.WelcoConversationMessage.ConversationId == conversation.Id)
        .order_by(models.WelcoConversationMessage.Id.asc())
        .all()
    )
    return schemas.WelcoConversationFullResponse(
        status=conversation.Status, messages=[_conv_message_out(m) for m in messages],
    )


@widget_router.get("/{public_id}/conversations/{conversation_id}/messages", response_model=schemas.WelcoConversationPollResponse)
def poll_conversation(
    public_id: str, conversation_id: int, after_id: int = 0, token: str = "", db: Session = Depends(get_db)
):
    conversation = _get_conversation_for_public_id(db, public_id, conversation_id, token)
    messages = (
        db.query(models.WelcoConversationMessage)
        .filter(
            models.WelcoConversationMessage.ConversationId == conversation.Id,
            models.WelcoConversationMessage.Id > after_id,
            models.WelcoConversationMessage.Sender == "human",
        )
        .order_by(models.WelcoConversationMessage.Id.asc())
        .all()
    )
    return schemas.WelcoConversationPollResponse(
        status=conversation.Status, messages=[_conv_message_out(m) for m in messages],
    )


@widget_router.post("/{public_id}/conversations/{conversation_id}/messages", status_code=201)
def add_visitor_message(
    public_id: str, conversation_id: int, body: schemas.WelcoConvMessageCreate, request: Request,
    token: str = "", db: Session = Depends(get_db),
):
    conversation = _get_conversation_for_public_id(db, public_id, conversation_id, token)
    if conversation.Status == "closed":
        raise HTTPException(400, "This conversation has ended")

    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip, public_id):
        raise HTTPException(429, "Too many messages, please try again later")

    db.add(models.WelcoConversationMessage(ConversationId=conversation.Id, Sender="visitor", Content=body.content))
    conversation.LastVisitorMessageAt = datetime.utcnow()
    db.commit()
    return {"status": "ok"}


@widget_router.post("/{public_id}/lead", status_code=201)
def widget_lead(public_id: str, body: schemas.WelcoLeadRequest, request: Request, db: Session = Depends(get_db)):
    if not body.email and not body.whatsapp:
        raise HTTPException(400, "Provide an email address or a WhatsApp number")

    # Public, unauthenticated, and it writes a row plus notifies the customer —
    # rate limited like every other visitor-facing write.
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip, public_id):
        raise HTTPException(429, "Too many requests, please try again later")

    kb = (
        db.query(models.WelcoKnowledgeBase)
        .filter(models.WelcoKnowledgeBase.PublicId == public_id)
        .first()
    )
    if kb is None:
        raise HTTPException(404, "Agent not found")

    lead_instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
    if lead_instance is None or not instance_subscription_active(db, lead_instance):
        raise HTTPException(402, "This agent is currently paused.")

    db.add(models.WelcoLead(
        ServiceInstanceId=kb.ServiceInstanceId,
        VisitorName=body.name,
        VisitorEmail=body.email,
        VisitorWhatsapp=body.whatsapp,
        Message=body.message,
    ))

    if body.conversation_id is not None:
        conversation = (
            db.query(models.WelcoConversation)
            .filter(
                models.WelcoConversation.Id == body.conversation_id,
                models.WelcoConversation.ServiceInstanceId == kb.ServiceInstanceId,
                models.WelcoConversation.Status == "waiting",
            )
            .first()
        )
        if conversation is not None:
            conversation.Status = "resolved_by_email"

    db.commit()

    _notify_new_lead(db, lead_instance, body)

    if body.conversation_id is None:
        # No conversation ever got created for this handoff (the widget's own
        # POST /conversations call must have failed) — this lead is the only
        # server-side signal we got, so it's the one place worth notifying from.
        instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
        if instance is not None:
            notifications.notify_instance(
                db, instance, "A visitor left their contact info — check your Welco leads.",
                event="welco_lead",
                data={
                    "instance_id": kb.ServiceInstanceId,
                    "name": body.name,
                    "email": body.email,
                    "whatsapp": body.whatsapp,
                    "message": body.message,
                },
            )

    notification_email = _instance_notification_email(db, kb.ServiceInstanceId)

    if notification_email:
        contact_lines = []
        if body.email:
            contact_lines.append(f"<b>Email:</b> {body.email}")
        if body.whatsapp:
            contact_lines.append(f"<b>WhatsApp:</b> {body.whatsapp}")
        contact_text = " / ".join([body.email or "", body.whatsapp or ""]).strip(" /")

        html_body = (
            f"<p>A visitor asked to be contacted via your WelcoChat widget:</p>"
            f"<p><b>Name:</b> {body.name or '-'}<br>"
            f"{'<br>'.join(contact_lines)}</p>"
            f"<p><b>Chat history:</b><br>{(body.message or '-').replace(chr(10), '<br>')}</p>"
        )
        text_body = f"New WelcoChat contact request — {body.name or '-'} ({contact_text}): {body.message or '-'}"
        send_email(
            subject="A visitor wants to be contacted — WelcoChat",
            email_to=notification_email,
            html_body=html_body,
            text_body=text_body,
        )

    return {"status": "ok"}


@widget_router.post("/{public_id}/whatsapp")
async def whatsapp_webhook(public_id: str, request: Request, db: Session = Depends(get_db)):
    kb = _get_ready_kb(db, public_id)
    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == kb.ServiceInstanceId).first()
    config = json.loads(instance.ConfigurationData) if instance and instance.ConfigurationData else {}

    account_sid = config.get("whatsapp_account_sid")
    auth_token = config.get("whatsapp_auth_token")
    whatsapp_number = config.get("whatsapp_number")
    if not (account_sid and auth_token and whatsapp_number):
        raise HTTPException(400, "WhatsApp is not configured for this agent")
    if instance is None or not instance_has_tier(db, instance, "Business"):
        # Plan was downgraded after WhatsApp was configured — decline quietly,
        # the same way rate-limited/already-handled-off messages are declined
        # below, rather than surfacing an error in Twilio's own console.
        return Response(content=whatsapp.empty_twiml(), media_type="application/xml; charset=utf-8")

    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    signature = request.headers.get("X-Twilio-Signature", "")
    if not whatsapp.verify_signature(auth_token, _whatsapp_webhook_url(public_id), params, signature):
        raise HTTPException(403, "Invalid signature")

    from_number = params.get("From", "").replace("whatsapp:", "").strip()
    body_text = params.get("Body", "").strip()
    if not from_number or not body_text:
        return Response(content=whatsapp.empty_twiml(), media_type="application/xml; charset=utf-8")

    if _rate_limited(from_number, public_id):
        return Response(content=whatsapp.empty_twiml(), media_type="application/xml; charset=utf-8")

    conversation = (
        db.query(models.WelcoConversation)
        .filter(
            models.WelcoConversation.ServiceInstanceId == kb.ServiceInstanceId,
            models.WelcoConversation.Channel == "whatsapp",
            models.WelcoConversation.VisitorPhone == from_number,
            models.WelcoConversation.Status != "closed",
        )
        .order_by(models.WelcoConversation.Id.desc())
        .first()
    )
    if conversation is None:
        conversation = models.WelcoConversation(
            ServiceInstanceId=kb.ServiceInstanceId, Status="bot", Channel="whatsapp", VisitorPhone=from_number,
        )
        db.add(conversation)
        db.flush()

    db.add(models.WelcoConversationMessage(ConversationId=conversation.Id, Sender="visitor", Content=body_text))
    conversation.LastVisitorMessageAt = datetime.utcnow()

    if conversation.Status != "bot":
        # Already handed off — a human will see this in Live Chat, no AI reply.
        db.commit()
        return Response(content=whatsapp.empty_twiml(), media_type="application/xml; charset=utf-8")

    db.commit()

    history_rows = (
        db.query(models.WelcoConversationMessage)
        .filter(models.WelcoConversationMessage.ConversationId == conversation.Id)
        .order_by(models.WelcoConversationMessage.Id.asc())
        .all()
    )
    history = [
        {"role": "user" if m.Sender == "visitor" else "assistant", "content": m.Content}
        for m in history_rows[:-1]
    ]

    kb_content = _build_kb_content(db, kb, config)
    widget_name = config.get("widget_name") or "Welco Assistant"

    try:
        reply_text, handoff = welco_engine.answer(
            kb_content=kb_content, history=history, message=body_text, widget_name=widget_name,
        )
    except RuntimeError:
        reply_text = "Sorry, I'm temporarily unavailable — a team member will follow up with you shortly."
        handoff = True

    db.add(models.WelcoConversationMessage(ConversationId=conversation.Id, Sender="agent", Content=reply_text))
    db.add(models.WelcoInteraction(ServiceInstanceId=kb.ServiceInstanceId, Handoff=handoff))

    if handoff:
        conversation.Status = "waiting"
        conversation.LastAgentMessageAt = datetime.utcnow()
        db.commit()
        _notify_handoff(db, instance, kb.ServiceInstanceId, conversation.Id, widget_name)
    else:
        db.commit()

    return Response(content=whatsapp.twiml_message(reply_text), media_type="application/xml; charset=utf-8")
