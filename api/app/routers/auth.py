# app/routers/auth.py
import re
import secrets
from datetime import datetime, timedelta

# International phone format, e.g. +36301234567 (leading + then 7-15 digits).
PHONE_RE = re.compile(r"\+[0-9]{7,15}")

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas, google_oauth
from ..deps import get_db, get_current_user
from ..security import (
    verify_password,
    get_password_hash,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


from ..email.service import (
    send_registration_email,
    send_password_reset_email,
    send_email_change_email,
)

router = APIRouter()


def _client_role_id(db: Session):
    """Az alapertelmezett 'Client' szerep Id-ja (uj user-ek ezt kapjak)."""
    role = db.query(models.Role).filter(models.Role.Name == "Client").first()
    return role.Id if role else None


def _log_login(db: Session, user_id: int):
    """Bejelentkezes naplozasa: melyik user mikor lepett be."""
    db.add(models.LoginLog(UserId=user_id))
    db.commit()


@router.post("/register", response_model=schemas.RegistrationResponse)
def register_user(
    req: schemas.RegistrationCreate,
    db: Session = Depends(get_db),
):
    # email foglaltság ellenőrzés a User-ben
    existing_user = (
        db.query(models.User)
        .filter(models.User.Email == req.email)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="There is already a user with this email address.",
        )

    # email foglaltság ellenőrzés a RegistrationRequest-ben
    existing_request = (
        db.query(models.RegistrationRequest)
        .filter(models.RegistrationRequest.Email == req.email)
        .first()
    )
    if existing_request:
        raise HTTPException(
            status_code=400,
            detail="Registration with this email address is already in progress.",
        )

    # generáljuk a 32 karakteres tokent
    token = secrets.token_hex(16)  # 32 hex karakter

    hashed_pw = get_password_hash(req.password)

    reg = models.RegistrationRequest(
        DisplayName=req.display_name,
        Email=req.email,
        Token=token,
        HashedPassword=hashed_pw,
    )

    db.add(reg)
    db.commit()

    # küldjünk megerősítő emailt
    try:
        send_registration_email(
            email_to=req.email,
            token=token,
            display_name=req.display_name
        )
    except Exception as e:
        db.delete(reg)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail="The confirmation email could not be sent. Please try again later.",
        ) from e


    return {"message": "Registration request created. Please confirm via email."}

@router.get("/verify-email")
def confirm_registration(token: str, db: Session = Depends(get_db)):
    # kérés megkeresése
    req = (
        db.query(models.RegistrationRequest)
        .filter(models.RegistrationRequest.Token == token)
        .first()
    )

    if not req:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired registration token.",
        )

    # új user beszúrása (alapból Client szereppel)
    user = models.User(
        DisplayName=req.DisplayName,
        Email=req.Email,
        HashedPassword=req.HashedPassword,
        IsActive=True,
        RoleId=_client_role_id(db),
    )

    db.add(user)

    # előző request törlése
    db.delete(req)

    db.commit()

    return {"message": "Registration confirmed. You can now log in."}


@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # OAuth2PasswordRequestForm -> username mezőben jön az email
    user = (
        db.query(models.User)
        .filter(models.User.Email == form_data.username)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.HashedPassword):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _log_login(db, user.Id)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.Email},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/google", response_model=schemas.Token)
def google_login(
    req: schemas.GoogleAuthRequest,
    db: Session = Depends(get_db),
):
    # A frontend a Google authorization code-ot és a hozzá használt redirect_uri-t
    # küldi; a backend cseréli a kódot Google-nél és kriptográfiailag igazolja az
    # id_token-t, mielőtt bármilyen identitást elhinne. Bármely hiba -> generikus
    # 401, hogy a Google-oldali belső hibák ne szivárogjanak ki.
    try:
        identity = google_oauth.exchange_code(req.code, req.redirect_uri)
    except google_oauth.GoogleAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = identity["email"]

    # find-or-create: a Google-azonosított felhasználó jelszó nélkül jön létre
    # (HashedPassword marad NULL), így csak Google-lel tud belépni amíg nem állít
    # be helyi jelszót.
    user = (
        db.query(models.User)
        .filter(models.User.Email == email)
        .first()
    )
    if not user:
        user = models.User(
            DisplayName=identity.get("name") or email.split("@", 1)[0],
            Email=email,
            HashedPassword=None,
            IsActive=True,
            RoleId=_client_role_id(db),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    _log_login(db, user.Id)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.Email},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserRead)
def read_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UpdateProfileResponse)
def update_me(
    req: schemas.UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Google-fiok (nincs helyi jelszo): az email NEM modosithato.
    is_google = current_user.HashedPassword is None

    if req.display_name is not None:
        name = req.display_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Display name cannot be empty.")
        current_user.DisplayName = name

    if req.phone is not None:
        phone = req.phone.strip()
        if phone and not PHONE_RE.fullmatch(phone):
            raise HTTPException(
                status_code=400,
                detail="Phone number must be in international format, e.g. +36301234567.",
            )
        current_user.Phone = phone or None

    email_change_pending = False
    if req.email is not None and req.email != current_user.Email:
        if is_google:
            raise HTTPException(
                status_code=400,
                detail="Email cannot be changed for Google accounts.",
            )
        taken = (
            db.query(models.User)
            .filter(models.User.Email == req.email, models.User.Id != current_user.Id)
            .first()
        )
        if taken:
            raise HTTPException(
                status_code=400, detail="This email address is already in use."
            )
        # Az email NEM valtozik azonnal: atmeneti tablaba kerul + megerosito email a
        # az UJ cimre; a tenyleges csere csak a megerositeskor tortenik.
        db.query(models.EmailChangeRequest).filter(
            models.EmailChangeRequest.UserId == current_user.Id
        ).delete()
        token = secrets.token_hex(16)
        db.add(
            models.EmailChangeRequest(
                UserId=current_user.Id, NewEmail=req.email, Token=token
            )
        )
        db.flush()
        try:
            send_email_change_email(
                email_to=req.email,
                token=token,
                display_name=current_user.DisplayName,
            )
            email_change_pending = True
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="The confirmation email could not be sent. Please try again later.",
            ) from e

    db.commit()
    db.refresh(current_user)

    # Uj token (a megjelenitett email valtozatlan, de egysegesseg kedveert frissitjuk).
    access_token = create_access_token(
        data={"sub": current_user.Email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "user": schemas.UserRead.model_validate(current_user),
        "access_token": access_token,
        "token_type": "bearer",
        "email_change_pending": email_change_pending,
    }


@router.get("/confirm-email-change", response_model=schemas.RegistrationResponse)
def confirm_email_change(token: str, db: Session = Depends(get_db)):
    change = (
        db.query(models.EmailChangeRequest)
        .filter(models.EmailChangeRequest.Token == token)
        .first()
    )
    if not change:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation link.")

    # lejarat: 1 ora
    if change.Created < datetime.utcnow() - timedelta(hours=1):
        db.delete(change)
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation link.")

    # az uj cim idokozben mas fiokhoz kerulhetett
    taken = (
        db.query(models.User)
        .filter(models.User.Email == change.NewEmail, models.User.Id != change.UserId)
        .first()
    )
    if taken:
        db.delete(change)
        db.commit()
        raise HTTPException(
            status_code=400, detail="This email address is already in use."
        )

    user = db.query(models.User).filter(models.User.Id == change.UserId).first()
    if not user:
        db.delete(change)
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation link.")

    user.Email = change.NewEmail
    db.delete(change)
    db.commit()

    return {"message": "Your email address has been updated. Please sign in again."}


@router.post("/change-password", response_model=schemas.RegistrationResponse)
def change_password(
    req: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Google-fiok: nincs helyi jelszo -> nem valtoztathato.
    if current_user.HashedPassword is None:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be changed for Google accounts.",
        )
    if not verify_password(req.current_password, current_user.HashedPassword):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    current_user.HashedPassword = get_password_hash(req.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


@router.post("/forgot-password", response_model=schemas.RegistrationResponse)
def forgot_password(req: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Generikus valasz minden esetben (nem szivarogtatjuk, letezik-e a fiok).
    user = (
        db.query(models.User)
        .filter(models.User.Email == req.email)
        .first()
    )
    if user:
        # korabbi fuggoben levo reset-tokenek torlese erre az emailre
        db.query(models.PasswordReset).filter(
            models.PasswordReset.Email == req.email
        ).delete()
        token = secrets.token_hex(16)  # 32 hex karakter
        db.add(models.PasswordReset(Email=req.email, Token=token))
        db.commit()
        try:
            send_password_reset_email(
                email_to=req.email,
                token=token,
                display_name=user.DisplayName,
            )
        except Exception:
            # az email-kuldes hibajat ne szivarogtassuk ki; a token elavulasig elhasznalhato
            pass

    return {"message": "If an account with this email exists, a reset link has been sent."}


@router.post("/reset-password", response_model=schemas.RegistrationResponse)
def reset_password(req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    reset = (
        db.query(models.PasswordReset)
        .filter(
            models.PasswordReset.Token == req.token,
            models.PasswordReset.Email == req.email,
        )
        .first()
    )
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    # token-lejarat: 1 ora
    if reset.Created < datetime.utcnow() - timedelta(hours=1):
        db.delete(reset)
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user = (
        db.query(models.User)
        .filter(models.User.Email == req.email)
        .first()
    )
    if not user:
        db.delete(reset)
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    user.HashedPassword = get_password_hash(req.password)
    db.delete(reset)
    db.commit()

    return {"message": "Password has been reset. You can now log in."}