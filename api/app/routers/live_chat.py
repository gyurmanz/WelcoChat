# app/routers/live_chat.py
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, whatsapp
from ..deps import get_db, get_current_user, resolve_account_company, instance_has_tier

router = APIRouter()

_STATUS_SORT_ORDER = {"waiting": 0, "active": 1, "resolved_by_email": 2, "closed": 3}


def _get_owned_conversation(db: Session, conversation_id: int, company_id: int) -> models.WelcoConversation:
    conversation = (
        db.query(models.WelcoConversation)
        .join(models.ServiceInstance, models.WelcoConversation.ServiceInstanceId == models.ServiceInstance.Id)
        .join(models.Subscription, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
        .filter(
            models.WelcoConversation.Id == conversation_id,
            models.Subscription.CompanyId == company_id,
        )
        .first()
    )
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    return conversation


def _message_out(m: models.WelcoConversationMessage) -> schemas.WelcoConvMessageRead:
    return schemas.WelcoConvMessageRead(
        id=m.Id, sender=m.Sender, sender_name=m.SenderName, content=m.Content, created=m.Created,
    )


def _instance_name(instance: models.ServiceInstance | None) -> str:
    if instance is None:
        return "Welco Assistant"
    config = json.loads(instance.ConfigurationData) if instance.ConfigurationData else {}
    return config.get("widget_name") or "Welco Assistant"


def _instance_names(db: Session, company_id: int) -> dict[int, str]:
    """One query for every Welco instance the owner has — avoids an N+1 lookup
    per conversation when building the list."""
    instances = (
        db.query(models.ServiceInstance)
        .join(models.Subscription, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
        .filter(models.Subscription.CompanyId == company_id, models.ServiceInstance.ServiceKey == "welco")
        .all()
    )
    return {i.Id: _instance_name(i) for i in instances}


def _detail_out(
    conversation: models.WelcoConversation, messages: list[models.WelcoConversationMessage], instance_name: str
) -> schemas.WelcoConversationDetail:
    return schemas.WelcoConversationDetail(
        id=conversation.Id, instance_id=conversation.ServiceInstanceId, instance_name=instance_name,
        status=conversation.Status, channel=conversation.Channel, visitor_phone=conversation.VisitorPhone,
        messages=[_message_out(m) for m in messages],
    )


@router.get("", response_model=list[schemas.WelcoConversationSummary])
def list_conversations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    conversations = (
        db.query(models.WelcoConversation)
        .join(models.ServiceInstance, models.WelcoConversation.ServiceInstanceId == models.ServiceInstance.Id)
        .join(models.Subscription, models.ServiceInstance.SubscriptionId == models.Subscription.Id)
        .filter(models.Subscription.CompanyId == company.Id, models.WelcoConversation.Status != "bot")
        .all()
    )
    instance_names = _instance_names(db, company.Id)

    summaries = []
    for c in conversations:
        last_message = (
            db.query(models.WelcoConversationMessage)
            .filter(models.WelcoConversationMessage.ConversationId == c.Id)
            .order_by(models.WelcoConversationMessage.Id.desc())
            .first()
        )
        preview = (last_message.Content[:140] if last_message else None)
        summaries.append((c, schemas.WelcoConversationSummary(
            id=c.Id,
            instance_id=c.ServiceInstanceId,
            instance_name=instance_names.get(c.ServiceInstanceId, "Welco Assistant"),
            status=c.Status,
            channel=c.Channel,
            visitor_phone=c.VisitorPhone,
            created=c.Created,
            last_visitor_message_at=c.LastVisitorMessageAt,
            last_agent_message_at=c.LastAgentMessageAt,
            preview=preview,
        )))

    def sort_key(pair):
        c, summary = pair
        last_activity = max(filter(None, [c.LastVisitorMessageAt, c.LastAgentMessageAt, c.Created]))
        return (_STATUS_SORT_ORDER.get(c.Status, 99), -last_activity.timestamp())

    summaries.sort(key=sort_key)
    return [s for _, s in summaries]


@router.get("/{conversation_id}", response_model=schemas.WelcoConversationDetail)
def get_conversation(
    conversation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    conversation = _get_owned_conversation(db, conversation_id, company.Id)
    messages = (
        db.query(models.WelcoConversationMessage)
        .filter(models.WelcoConversationMessage.ConversationId == conversation.Id)
        .order_by(models.WelcoConversationMessage.Id.asc())
        .all()
    )
    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == conversation.ServiceInstanceId).first()
    return _detail_out(conversation, messages, _instance_name(instance))


@router.post("/{conversation_id}/messages", response_model=schemas.WelcoConvMessageRead, status_code=201)
def reply(
    conversation_id: int,
    body: schemas.WelcoConvMessageCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    conversation = _get_owned_conversation(db, conversation_id, company.Id)
    if conversation.Status == "closed":
        raise HTTPException(400, "This conversation has ended")

    if conversation.Channel == "whatsapp":
        instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == conversation.ServiceInstanceId).first()
        if instance is None or not instance_has_tier(db, instance, "Business"):
            raise HTTPException(403, "Upgrade to Business to reply via WhatsApp.")
        config = json.loads(instance.ConfigurationData) if instance.ConfigurationData else {}
        account_sid = config.get("whatsapp_account_sid")
        auth_token = config.get("whatsapp_auth_token")
        whatsapp_number = config.get("whatsapp_number")
        if not (account_sid and auth_token and whatsapp_number and conversation.VisitorPhone):
            raise HTTPException(400, "WhatsApp is not configured for this agent")
        try:
            whatsapp.send_whatsapp_message(account_sid, auth_token, whatsapp_number, conversation.VisitorPhone, body.content)
        except Exception:
            raise HTTPException(502, "Failed to deliver the WhatsApp message — please try again.")

    message = models.WelcoConversationMessage(
        ConversationId=conversation.Id, Sender="human", SenderName=current_user.DisplayName, Content=body.content,
    )
    db.add(message)
    conversation.Status = "active"
    conversation.LastAgentMessageAt = datetime.utcnow()
    db.commit()
    db.refresh(message)
    return _message_out(message)


@router.post("/{conversation_id}/close", response_model=schemas.WelcoConversationDetail)
def close_conversation(
    conversation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = resolve_account_company(db, current_user)
    conversation = _get_owned_conversation(db, conversation_id, company.Id)
    conversation.Status = "closed"
    db.commit()

    instance = db.query(models.ServiceInstance).filter(models.ServiceInstance.Id == conversation.ServiceInstanceId).first()
    messages = (
        db.query(models.WelcoConversationMessage)
        .filter(models.WelcoConversationMessage.ConversationId == conversation.Id)
        .order_by(models.WelcoConversationMessage.Id.asc())
        .all()
    )
    return _detail_out(conversation, messages, _instance_name(instance))
