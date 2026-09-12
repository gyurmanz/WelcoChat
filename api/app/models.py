# app/models.py
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text,
)
from datetime import datetime
from .database import Base


class RegistrationRequest(Base):
    __tablename__ = "RegistrationRequest"

    Id = Column(Integer, primary_key=True, index=True)
    DisplayName = Column(String(100), nullable=False)
    Email = Column(String(100), nullable=False)
    Token = Column(String(32), unique=True, nullable=False)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    HashedPassword = Column(String(255), nullable=False)


class Role(Base):
    __tablename__ = "Role"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(50), nullable=False)


class Country(Base):
    __tablename__ = "Country"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(100), nullable=False)
    Code = Column(String(2), nullable=False)


class Company(Base):
    """The billing/subscription root. A User always belongs to exactly one
    Company (their own, created at signup, or one they joined via a team
    invite) — Subscriptions, the Stripe customer identity, and team
    membership all key off Company.Id, not any individual User.Id."""
    __tablename__ = "Company"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(200), nullable=False)
    CountryId = Column(Integer, ForeignKey("Country.Id"), nullable=True)
    PostalCode = Column(String(20), nullable=True)
    City = Column(String(100), nullable=True)
    AddressLine = Column(String(200), nullable=True)
    TaxNumber = Column(String(50), nullable=True)
    OwnerUserId = Column(Integer, ForeignKey("User.Id"), nullable=True)
    StripeCustomerId = Column(String(60), nullable=True)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class User(Base):
    __tablename__ = "User"

    Id = Column(Integer, primary_key=True, index=True)
    DisplayName = Column(String(100), nullable=False)
    Email = Column(String(100), nullable=False)
    IsActive = Column(Boolean, nullable=False, default=True)
    HashedPassword = Column(String(255), nullable=True)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    RoleId = Column(Integer, ForeignKey("Role.Id"), nullable=True)
    CompanyId = Column(Integer, ForeignKey("Company.Id"), nullable=True)
    Phone = Column(String(50), nullable=True)

    @property
    def has_password(self) -> bool:
        return self.HashedPassword is not None


class Service(Base):
    __tablename__ = "Service"

    Id = Column(Integer, primary_key=True, index=True)
    ServiceKey = Column(String(30), nullable=False)
    ServiceName = Column(String(100), nullable=False)
    Tier = Column(String(20), nullable=False)
    MonthlyPrice = Column(Numeric(18, 2), nullable=False)
    AnnualPrice = Column(Numeric(18, 2), nullable=False)
    SortOrder = Column(Integer, nullable=False)
    IsActive = Column(Boolean, nullable=False, default=True)
    StripePriceIdMonthly = Column(String(60), nullable=True)
    StripePriceIdAnnual = Column(String(60), nullable=True)
    # Conversations/month included in the plan, as advertised on the pricing
    # page. NULL means unmetered.
    MonthlyConversationLimit = Column(Integer, nullable=True)


class Subscription(Base):
    __tablename__ = "Subscription"

    Id = Column(Integer, primary_key=True, index=True)
    CompanyId = Column(Integer, ForeignKey("Company.Id"), nullable=False, index=True)
    # Audit only — who actually clicked "start trial"/checkout. Ownership and
    # access control always go through CompanyId, never this.
    UserId = Column(Integer, ForeignKey("User.Id"), nullable=False, index=True)
    Type = Column(String(50), nullable=False)
    Status = Column(String(20), nullable=False, default="active")
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    ServiceId = Column(Integer, ForeignKey("Service.Id"), nullable=True)
    BillingPeriod = Column(String(20), nullable=True)
    PaidPrice = Column(Numeric(18, 2), nullable=True)
    StartDate = Column(DateTime, nullable=True)
    EndDate = Column(DateTime, nullable=True)
    TrialEndsAt = Column(DateTime, nullable=True)
    StripeSubscriptionId = Column(String(60), nullable=True)
    PendingServiceId = Column(Integer, ForeignKey("Service.Id"), nullable=True)
    PendingBillingPeriod = Column(String(20), nullable=True)
    # Promo code entered at trial signup (e.g. a launch-campaign code) — kept
    # for reporting on which channel/campaign drove the signup. The actual
    # discount lives on the Stripe subscription itself, not here.
    PromoCode = Column(String(50), nullable=True)
    # Which trial-ending reminder has already gone out ("trial-3d"/"trial-1d"),
    # so a cron that runs twice doesn't email the customer twice.
    TrialReminderSent = Column(String(20), nullable=True)


class ServiceInstance(Base):
    """One workflow module the user can configure. Suite creates 4 of these under 1 Subscription."""
    __tablename__ = "ServiceInstance"

    Id = Column(Integer, primary_key=True, index=True)
    SubscriptionId = Column(Integer, ForeignKey("Subscription.Id"), nullable=False, index=True)
    ServiceKey = Column(String(30), nullable=False)
    ServiceName = Column(String(100), nullable=False)
    SetupStatus = Column(String(30), nullable=False, default="not_configured")
    ConfigurationData = Column(Text, nullable=True)
    # "YYYY-MM" of the month whose quota warning has already been emailed, so
    # crossing the line notifies the customer once instead of per message.
    QuotaNoticeMonth = Column(String(7), nullable=True)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class WelcoKnowledgeBase(Base):
    __tablename__ = "WelcoKnowledgeBase"

    Id = Column(Integer, primary_key=True, index=True)
    ServiceInstanceId = Column(Integer, ForeignKey("ServiceInstance.Id"), nullable=False, unique=True, index=True)
    PublicId = Column(String(36), nullable=False, unique=True, index=True)
    Status = Column(String(20), nullable=False, default="pending")
    SourceUrl = Column(String(500), nullable=True)
    Content = Column(Text, nullable=True)
    PageCount = Column(Integer, nullable=True)
    ErrorMessage = Column(String(500), nullable=True)
    CrawledAt = Column(DateTime, nullable=True)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class WelcoLead(Base):
    __tablename__ = "WelcoLead"

    Id = Column(Integer, primary_key=True, index=True)
    ServiceInstanceId = Column(Integer, ForeignKey("ServiceInstance.Id"), nullable=False, index=True)
    VisitorName = Column(String(200), nullable=True)
    VisitorEmail = Column(String(200), nullable=True)
    VisitorWhatsapp = Column(String(50), nullable=True)
    Message = Column(Text, nullable=True)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class WelcoDocument(Base):
    __tablename__ = "WelcoDocument"

    Id = Column(Integer, primary_key=True, index=True)
    ServiceInstanceId = Column(Integer, ForeignKey("ServiceInstance.Id"), nullable=False, index=True)
    FileName = Column(String(255), nullable=False)
    ExtractedText = Column(Text, nullable=True)
    CharCount = Column(Integer, nullable=True)
    UploadedAt = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class WelcoInteraction(Base):
    """One row per answered widget message — no content, no visitor id, just enough for stats."""
    __tablename__ = "WelcoInteraction"

    Id = Column(Integer, primary_key=True, index=True)
    ServiceInstanceId = Column(Integer, ForeignKey("ServiceInstance.Id"), nullable=False, index=True)
    Handoff = Column(Boolean, nullable=False, default=False)
    # Groups the messages of one visitor chat together. Plans are sold per
    # conversation, not per message, so the quota counts distinct values of
    # this per calendar month. Opaque and visitor-generated — not an identity.
    SessionId = Column(String(64), nullable=True, index=True)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class WelcoConversation(Base):
    """A handoff conversation a portal user can join and reply to live (via polling)."""
    __tablename__ = "WelcoConversation"

    Id = Column(Integer, primary_key=True, index=True)
    ServiceInstanceId = Column(Integer, ForeignKey("ServiceInstance.Id"), nullable=False, index=True)
    Status = Column(String(20), nullable=False, default="waiting")
    Channel = Column(String(10), nullable=False, default="widget")  # widget | whatsapp
    VisitorPhone = Column(String(30), nullable=True)
    # Unguessable per-conversation secret. The visitor-facing endpoints are
    # public and keyed by a sequential Id, so without this any visitor on the
    # customer's site could read — and post into — every other visitor's
    # conversation just by counting up.
    Token = Column(String(64), nullable=True, unique=True, index=True)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    LastVisitorMessageAt = Column(DateTime, nullable=True)
    LastAgentMessageAt = Column(DateTime, nullable=True)


class WelcoConversationMessage(Base):
    __tablename__ = "WelcoConversationMessage"

    Id = Column(Integer, primary_key=True, index=True)
    ConversationId = Column(Integer, ForeignKey("WelcoConversation.Id"), nullable=False, index=True)
    Sender = Column(String(10), nullable=False)  # visitor | agent | human
    SenderName = Column(String(100), nullable=True)
    Content = Column(Text, nullable=False)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class AccountMember(Base):
    __tablename__ = "AccountMember"

    Id = Column(Integer, primary_key=True, index=True)
    CompanyId = Column(Integer, ForeignKey("Company.Id"), nullable=False, index=True)
    MemberUserId = Column(Integer, ForeignKey("User.Id"), nullable=True, index=True)
    InviteEmail = Column(String(100), nullable=False)
    InviteToken = Column(String(32), nullable=True)
    Status = Column(String(20), nullable=False, default="invited")
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    AcceptedAt = Column(DateTime, nullable=True)


class EmailChangeRequest(Base):
    __tablename__ = "EmailChangeRequest"

    Id = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, ForeignKey("User.Id"), nullable=False, index=True)
    NewEmail = Column(String(100), nullable=False)
    Token = Column(String(32), nullable=False)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class LoginLog(Base):
    __tablename__ = "LoginLog"

    Id = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, ForeignKey("User.Id"), nullable=False, index=True)
    LoginAt = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class PasswordReset(Base):
    __tablename__ = "PasswordReset"

    Id = Column(Integer, primary_key=True, index=True)
    Email = Column(String(100), nullable=False)
    Token = Column(String(32), nullable=False)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )


class PushSubscription(Base):
    """A browser Push API subscription for one logged-in portal user (one row
    per browser/device that opted in) — used to send an OS-level notification
    on a live handoff when the portal is installed as a PWA / running in the
    background."""
    __tablename__ = "PushSubscription"

    Id = Column(Integer, primary_key=True, index=True)
    UserId = Column(Integer, ForeignKey("User.Id"), nullable=False, index=True)
    Endpoint = Column(String(500), unique=True, nullable=False)
    P256dh = Column(String(255), nullable=False)
    Auth = Column(String(255), nullable=False)
    Created = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
