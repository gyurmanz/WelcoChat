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
    __tablename__ = "Company"

    Id = Column(Integer, primary_key=True, index=True)
    Name = Column(String(200), nullable=False)
    CountryId = Column(Integer, ForeignKey("Country.Id"), nullable=True)
    PostalCode = Column(String(20), nullable=True)
    City = Column(String(100), nullable=True)
    AddressLine = Column(String(200), nullable=True)
    TaxNumber = Column(String(50), nullable=True)
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
    StripeCustomerId = Column(String(60), nullable=True)

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


class Subscription(Base):
    __tablename__ = "Subscription"

    Id = Column(Integer, primary_key=True, index=True)
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


class ServiceInstance(Base):
    """One workflow module the user can configure. Suite creates 4 of these under 1 Subscription."""
    __tablename__ = "ServiceInstance"

    Id = Column(Integer, primary_key=True, index=True)
    SubscriptionId = Column(Integer, ForeignKey("Subscription.Id"), nullable=False, index=True)
    ServiceKey = Column(String(30), nullable=False)
    ServiceName = Column(String(100), nullable=False)
    SetupStatus = Column(String(30), nullable=False, default="not_configured")
    ConfigurationData = Column(Text, nullable=True)
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
    OwnerUserId = Column(Integer, ForeignKey("User.Id"), nullable=False, index=True)
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
