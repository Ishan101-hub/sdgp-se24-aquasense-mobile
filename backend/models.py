# app/models.py
# AquaSense v2 – SQLAlchemy ORM Models

from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean,
    Numeric, Text, ForeignKey, Date, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role          = Column(String(20), nullable=False, default="user")
    is_active     = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    networks       = relationship("Network", back_populates="owner", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, unique=True, nullable=False)
    issued_at  = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


# ── Networks ──────────────────────────────────────────────────────────────────
class Network(Base):
    __tablename__ = "networks"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    location   = Column(String(200))
    owner_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner   = relationship("User", back_populates="networks")
    devices = relationship("Device", back_populates="network", cascade="all, delete-orphan")


# ── Devices ───────────────────────────────────────────────────────────────────
class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True, index=True)
    network_id   = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    device_id    = Column(String(50), unique=True, nullable=False, index=True)
    subline_name = Column(String(100))
    status       = Column(String(20), default="active", nullable=False)
    valve_state  = Column(String(10), default="open", nullable=False)
    installed_at = Column(DateTime(timezone=True), server_default=func.now())

    network         = relationship("Network", back_populates="devices")
    readings        = relationship("Reading", back_populates="device", cascade="all, delete-orphan")
    events          = relationship("Event", back_populates="device", cascade="all, delete-orphan")
    valve_logs      = relationship("ValveLog", back_populates="device", cascade="all, delete-orphan")
    daily_summaries = relationship("DailySummary", back_populates="device", cascade="all, delete-orphan")


# ── Readings (partitioned – ORM maps to parent table) ────────────────────────
class Reading(Base):
    __tablename__ = "readings"

    id           = Column(BigInteger, primary_key=True)
    device_id    = Column(String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    flow_rate    = Column(Numeric(10, 4), nullable=False)
    total_volume = Column(Numeric(14, 4), nullable=False)
    valve_status = Column(String(10), nullable=False)
    timestamp    = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("device_id", "timestamp", name="uq_reading_device_ts"),
    )

    device = relationship("Device", back_populates="readings")


# ── Daily Summaries ───────────────────────────────────────────────────────────
class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id                  = Column(Integer, primary_key=True)
    device_id           = Column(String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    summary_date        = Column(Date, nullable=False)
    total_volume_litres = Column(Numeric(14, 4), default=0)
    avg_flow_rate       = Column(Numeric(10, 4))
    max_flow_rate       = Column(Numeric(10, 4))
    min_flow_rate       = Column(Numeric(10, 4))
    reading_count       = Column(Integer, default=0)
    leak_event_count    = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("device_id", "summary_date", name="uq_daily_summary"),
    )

    device = relationship("Device", back_populates="daily_summaries")


# ── Events ────────────────────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = "events"

    id          = Column(Integer, primary_key=True, index=True)
    device_id   = Column(String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    network_id  = Column(Integer, ForeignKey("networks.id", ondelete="SET NULL"), nullable=True)
    event_type  = Column(String(40), nullable=False)
    severity    = Column(String(10), default="medium", nullable=False)
    description = Column(Text)
    resolved    = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    timestamp   = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="events")


# ── Valve Logs ────────────────────────────────────────────────────────────────
class ValveLog(Base):
    __tablename__ = "valve_logs"

    id              = Column(Integer, primary_key=True)
    device_id       = Column(String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    commanded_by    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action          = Column(String(10), nullable=False)
    source          = Column(String(20), default="manual", nullable=False)
    commanded_at    = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", back_populates="valve_logs")
