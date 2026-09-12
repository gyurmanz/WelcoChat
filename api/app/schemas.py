# app/schemas.py
from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, EmailStr, StringConstraints, Field, ConfigDict

# -------------------------------------------------------------------
# User schemas
# -------------------------------------------------------------------

class UserBase(BaseModel):
    # ORM attribútumok: Email, DisplayName
    # API mezők: email, display_name
    email: EmailStr = Field(validation_alias="Email", serialization_alias="email")
    display_name: str = Field(validation_alias="DisplayName", serialization_alias="display_name")
    phone: Optional[str] = Field(
        default=None, validation_alias="Phone", serialization_alias="phone"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserCreate(UserBase):
    password: Annotated[str, StringConstraints(min_length=8)]


class UserRead(UserBase):
    # ORM attribútumok: Id, IsActive, has_password (property)
    # API mezők: id, is_active, has_password
    id: int = Field(validation_alias="Id", serialization_alias="id")
    is_active: bool = Field(validation_alias="IsActive", serialization_alias="is_active")
    has_password: bool = Field(
        validation_alias="has_password", serialization_alias="has_password"
    )


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: Annotated[str, StringConstraints(min_length=8)]


class UpdateProfileResponse(BaseModel):
    user: UserRead
    access_token: str
    token_type: str
    email_change_pending: bool = False


# -------------------------------------------------------------------
# Registration schemas
# -------------------------------------------------------------------

class RegistrationCreate(BaseModel):
    # request body a frontendtől
    display_name: str
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=8)]


class RegistrationResponse(BaseModel):
    message: str


# -------------------------------------------------------------------
# Auth / token schemas
# -------------------------------------------------------------------

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# -------------------------------------------------------------------
# Google OAuth schemas
# -------------------------------------------------------------------

class GoogleAuthRequest(BaseModel):
    # A frontend a Google-redirectből kapott egyszer-használatos kódot és az
    # ahhoz használt redirect_uri-t küldi; a kódcserét a backend végzi a
    # bizalmas client_secret-tel (lásd app/google_oauth.py).
    code: str
    redirect_uri: str


# -------------------------------------------------------------------
# Password reset schemas
# -------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=8)]


# -------------------------------------------------------------------
# Billing: Country + Company schemas
# -------------------------------------------------------------------

class CountryRead(BaseModel):
    id: int = Field(validation_alias="Id", serialization_alias="id")
    name: str = Field(validation_alias="Name", serialization_alias="name")
    code: str = Field(validation_alias="Code", serialization_alias="code")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CompanyRead(BaseModel):
    id: int = Field(validation_alias="Id", serialization_alias="id")
    name: str = Field(validation_alias="Name", serialization_alias="name")
    country_id: Optional[int] = Field(
        default=None, validation_alias="CountryId", serialization_alias="country_id"
    )
    postal_code: Optional[str] = Field(
        default=None, validation_alias="PostalCode", serialization_alias="postal_code"
    )
    city: Optional[str] = Field(
        default=None, validation_alias="City", serialization_alias="city"
    )
    address_line: Optional[str] = Field(
        default=None, validation_alias="AddressLine", serialization_alias="address_line"
    )
    tax_number: Optional[str] = Field(
        default=None, validation_alias="TaxNumber", serialization_alias="tax_number"
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CompanyUpsert(BaseModel):
    name: str
    country_id: Optional[int] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    address_line: Optional[str] = None
    tax_number: Optional[str] = None


# -------------------------------------------------------------------
# Subscriptions
# -------------------------------------------------------------------

class ServicePlanRead(BaseModel):
    id: int
    service_key: str
    service_name: str
    tier: str
    monthly_price: float
    annual_price: float


class SubscriptionRead(BaseModel):
    id: int
    service_id: Optional[int] = None
    service_key: Optional[str] = None
    service_name: Optional[str] = None
    tier: Optional[str] = None
    billing_period: Optional[str] = None
    paid_price: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    status: str
    created: datetime
    pending_tier: Optional[str] = None
    pending_billing_period: Optional[str] = None


class TrialEligibilityRead(BaseModel):
    welco: bool


class TrialSubscriptionCreate(BaseModel):
    service_key: str  # welco — trial is always the Business tier
    promo_code: Optional[str] = None


class CheckoutSessionCreate(BaseModel):
    service_id: int
    billing_period: str  # monthly | annual


class CheckoutSessionRead(BaseModel):
    checkout_url: str


class ChangePlanRequest(BaseModel):
    new_service_id: int
    billing_period: Optional[str] = None  # monthly | annual — omit to keep the current period


class InvoiceRead(BaseModel):
    id: str
    number: Optional[str] = None
    issued_date: Optional[datetime] = None
    period: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: str
    pdf_url: Optional[str] = None


class AccountDeleteRequest(BaseModel):
    confirm_email: str


class PortalSessionRead(BaseModel):
    url: str


# -------------------------------------------------------------------
# Public contact / demo request (kaptila.com landing form)
# -------------------------------------------------------------------

class ContactRequest(BaseModel):
    name: str
    company: str
    email: EmailStr
    website: Optional[str] = None
    phone: Optional[str] = None
    service: Optional[str] = None
    message: Optional[str] = None
    volume: Optional[str] = None
    pilot_type: Optional[str] = None


# -------------------------------------------------------------------
# ServiceInstance schemas
# -------------------------------------------------------------------

class ServiceInstanceRead(BaseModel):
    id: int
    subscription_id: int
    service_key: str
    service_name: str
    setup_status: str
    tier: str
    configuration: Optional[dict] = None


class ServiceInstanceSetup(BaseModel):
    setup_status: Optional[str] = None
    configuration: Optional[dict] = None


# -------------------------------------------------------------------
# Kaptila Welco engine
# -------------------------------------------------------------------

class WelcoStatusRead(BaseModel):
    status: str
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    embed_snippet: Optional[str] = None
    whatsapp_webhook_url: Optional[str] = None


class WelcoChatMessage(BaseModel):
    role: str
    content: str


class WelcoMessageRequest(BaseModel):
    history: list[WelcoChatMessage] = []
    message: Annotated[str, StringConstraints(min_length=0, max_length=2000)] = ""
    image_data: Optional[str] = None  # base64, no data: URI prefix
    image_media_type: Optional[str] = None  # image/png | image/jpeg | image/webp | image/gif
    # Opaque id the widget generates per visitor chat, so messages can be
    # grouped into conversations for the plan's monthly allowance.
    session_id: Annotated[str, StringConstraints(max_length=64)] = ""


class WelcoMessageResponse(BaseModel):
    reply: str
    handoff: bool


class WelcoWidgetConfig(BaseModel):
    widget_name: str
    widget_color: str
    widget_bg_color: str
    widget_theme: str
    greeting_message: str
    widget_logo_url: Optional[str] = None
    widget_position: str = "bottom-right"
    widget_custom_css: Optional[str] = None
    image_upload_enabled: bool = False
    # "" = follow the visitor's browser language
    widget_language: str = ""


class WelcoLogoUploadResult(BaseModel):
    logo_url: str


class WelcoLeadRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    message: Optional[str] = None
    conversation_id: Optional[int] = None


class WelcoConvMessageCreate(BaseModel):
    content: Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class WelcoConvMessageRead(BaseModel):
    id: int
    sender: str
    sender_name: Optional[str] = None
    content: str
    created: datetime


class WelcoConversationCreate(BaseModel):
    history: list[WelcoChatMessage] = []


class WelcoConversationCreateResponse(BaseModel):
    conversation_id: int
    conversation_token: str
    last_message_id: int


class WelcoConversationPollResponse(BaseModel):
    status: str
    messages: list[WelcoConvMessageRead]


class WelcoConversationFullResponse(BaseModel):
    status: str
    messages: list[WelcoConvMessageRead]


class WelcoConversationSummary(BaseModel):
    id: int
    instance_id: int
    instance_name: str
    status: str
    channel: str
    visitor_phone: Optional[str] = None
    created: datetime
    last_visitor_message_at: Optional[datetime] = None
    last_agent_message_at: Optional[datetime] = None
    preview: Optional[str] = None


class WelcoConversationDetail(BaseModel):
    id: int
    instance_id: int
    instance_name: str
    status: str
    channel: str
    visitor_phone: Optional[str] = None
    messages: list[WelcoConvMessageRead]


# -------------------------------------------------------------------
# Notifications (Slack/Teams webhook)
# -------------------------------------------------------------------

class NotificationTestRequest(BaseModel):
    channel_type: str
    webhook_url: str


class WelcoDocumentRead(BaseModel):
    id: int
    file_name: str
    char_count: Optional[int] = None
    uploaded_at: datetime


class WelcoDocumentUploadResult(BaseModel):
    file_name: str
    id: Optional[int] = None
    char_count: Optional[int] = None
    error: Optional[str] = None


# -------------------------------------------------------------------
# Team accounts
# -------------------------------------------------------------------

class TeamMemberRead(BaseModel):
    id: int
    email: str
    display_name: Optional[str] = None
    status: str
    created: datetime


class TeamListResponse(BaseModel):
    is_owner: bool
    tier_eligible: bool
    members: list[TeamMemberRead]


class TeamInviteRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class InviteDetailsRead(BaseModel):
    invite_email: str
    owner_display_name: str


class AcceptInviteRequest(BaseModel):
    token: str
    display_name: str
    password: Annotated[str, StringConstraints(min_length=8)]


# -------------------------------------------------------------------
# Statistics
# -------------------------------------------------------------------

class DailyCount(BaseModel):
    date: str
    count: int


class WelcoLeadRead(BaseModel):
    id: int
    instance_id: int
    instance_name: str
    name: Optional[str] = None
    email: Optional[str] = None
    whatsapp: Optional[str] = None
    message: Optional[str] = None
    created: datetime


class WelcoStatsRead(BaseModel):
    instance_id: int
    total_messages: int
    messages_last_30d: int
    handoff_rate: float
    total_leads: int
    leads_last_30d: int
    page_count: Optional[int] = None
    document_count: int
    kb_status: str
    crawled_at: Optional[datetime] = None
    daily_messages: list[DailyCount]
    conversations_this_month: int = 0
    conversation_limit: Optional[int] = None  # None = unmetered plan


class StatsResponse(BaseModel):
    welco: list[WelcoStatsRead]


# -------------------------------------------------------------------
# Push notifications (Web Push / PWA)
# -------------------------------------------------------------------

class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class VapidPublicKeyRead(BaseModel):
    public_key: str
