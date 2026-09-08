# app/routers/push.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..deps import get_db, get_current_user
from ..push_service import VAPID_PUBLIC_KEY

router = APIRouter()


@router.get("/vapid-public-key", response_model=schemas.VapidPublicKeyRead)
def vapid_public_key(current_user: models.User = Depends(get_current_user)):
    return schemas.VapidPublicKeyRead(public_key=VAPID_PUBLIC_KEY)


@router.post("/subscribe", status_code=204)
def subscribe(
    body: schemas.PushSubscriptionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(models.PushSubscription)
        .filter(models.PushSubscription.Endpoint == body.endpoint)
        .first()
    )
    if existing:
        existing.UserId = current_user.Id
        existing.P256dh = body.keys.p256dh
        existing.Auth = body.keys.auth
    else:
        db.add(models.PushSubscription(
            UserId=current_user.Id,
            Endpoint=body.endpoint,
            P256dh=body.keys.p256dh,
            Auth=body.keys.auth,
        ))
    db.commit()


@router.post("/unsubscribe", status_code=204)
def unsubscribe(
    body: schemas.PushUnsubscribeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(models.PushSubscription).filter(
        models.PushSubscription.Endpoint == body.endpoint,
        models.PushSubscription.UserId == current_user.Id,
    ).delete()
    db.commit()
