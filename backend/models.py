# models.py
# AquaSense v3.1 — SQLAlchemy ORM Models
#
# Auth changes to support Kulith's authentication system:
#   • User gains: name, phone_encrypted, address_encrypted, profile_picture,
#                 is_verified, otp, otp_expires_at, otp_type,
#                 two_fa_enabled, login_alerts, auto_lock_minutes,
#                 terms_*, district, google_id
#   • RefreshToken removed (Kulith uses blacklisting instead of stored hashes)
#   • BlacklistedToken added  (replaces RefreshToken + MongoDB blacklist)
#   • FailedAttempt added     (account lockout after N wrong passwords)
#
# IoT hierarchy unchanged: Network → Zone → Device → Reading

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Index, Integer, BigInteger, Numeric, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────────────────────
#  USER
#  All fields from Kulith's MongoDB user document preserved.
#  Sensitive fields (phone, address) stored encrypted via Fernet.
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True)

    # ── Core identity ─────────────────────────────────────────
    name            = Column(String(50),  nullable=False, default="")
    email           = Column(String(150), unique=True, nullable=False, index=True)
    password_hash   = Column(Text, nullable=False)

    # ── Contact (encrypted at rest using Fernet) ──────────────
    phone_encrypted   = Column(Text, nullable=True)
    address_encrypted = Column(Text, nullable=True)

    # ── Profile ───────────────────────────────────────────────
    profile_picture = Column(String(500), nullable=True)
    district        = Column(String(50),  nullable=True)

    # ── Account state ─────────────────────────────────────────
    is_verified     = Column(Boolean, default=False, nullable=False)
    role            = Column(String(20), nullable=False, default="user")

    # ── OTP (verification / password reset / 2FA) ─────────────
    otp             = Column(String(6),  nullable=True)
    otp_expires_at  = Column(DateTime(timezone=True), nullable=True)
    otp_type        = Column(String(20), nullable=True)  # "verification"|"reset"|"2fa"

    # ── Security settings ─────────────────────────────────────
    two_fa_enabled    = Column(Boolean, default=False, nullable=False)
    login_alerts      = Column(Boolean, default=False, nullable=False)
    auto_lock_minutes = Column(Integer, default=5,     nullable=False)

    # ── Terms and conditions ──────────────────────────────────
    terms_of_service    = Column(Boolean, default=False, nullable=False)
    privacy_policy      = Column(Boolean, default=False, nullable=False)
    iot_data_collection = Column(Boolean, default=False, nullable=False)
    cookie_policy       = Column(Boolean, default=False, nullable=False)
    tips_and_updates    = Column(Boolean, default=False, nullable=False)

    # ── Google OAuth ──────────────────────────────────────────
    google_id       = Column(String(200), unique=True, nullable=True)

    # ── Timestamps ────────────────────────────────────────────
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now())

    networks = relationship("Network", back_populates="owner", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
#  BLACKLISTED TOKENS
#  Replaces both the old RefreshToken table and Kulith's
#  MongoDB blacklisted_tokens_collection.
#
#  Stores tokens invalidated by logout.
#  Every protected request checks this table before allowing access.
#  Rows older than 7 days can be pruned (max token lifespan).
# ─────────────────────────────────────────────────────────────

class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    id             = Column(Integer, primary_key=True)
    token          = Column(Text, unique=True, nullable=False)
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Fast lookup on every protected request: WHERE token = ?
        Index("ix_blacklisted_tokens_token", "token"),
    )


# ─────────────────────────────────────────────────────────────
#  FAILED ATTEMPTS
#  Replaces Kulith's MongoDB failed_attempts_collection.
#  Tracks failed login attempts per identifier (email or phone).
#  Locks account after MAX_FAILED_ATTEMPTS failures.
# ─────────────────────────────────────────────────────────────

class FailedAttempt(Base):
    __tablename__ = "failed_attempts"

    id           = Column(Integer, primary_key=True)
    identifier   = Column(String(150), nullable=False, index=True)
    attempts     = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_attempt = Column(DateTime(timezone=True), server_default=func.now(),
                          onupdate=func.now())


# ─────────────────────────────────────────────────────────────
#  NETWORK
# ─────────────────────────────────────────────────────────────

class Network(Base):
    __tablename__ = "networks"

    id         = Column(Integer, primary_key=True)
    network_id = Column(String(80), unique=True, nullable=False, index=True)
    name       = Column(String(100), nullable=False)
    location   = Column(String(200))
    owner_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="networks")
    zones = relationship("Zone", back_populates="network", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
#  ZONE
# ─────────────────────────────────────────────────────────────

class Zone(Base):
    __tablename__ = "zones"

    id         = Column(Integer, primary_key=True)
    zone_id    = Column(String(80), nullable=False, index=True)
    zone_name  = Column(String(100), nullable=False)
    zone_type  = Column(String(50),  nullable=False, default="general")
    floor      = Column(String(50),  nullable=True)
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    network = relationship("Network", back_populates="zones")
    devices = relationship("Device",  back_populates="zone", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("network_id", "zone_id", name="uq_zone_per_network"),
        Index("ix_zones_network_zone",      "network_id", "zone_id"),
        Index("ix_zones_network_zone_type", "network_id", "zone_type"),
    )


# ─────────────────────────────────────────────────────────────
#  DEVICE
# ─────────────────────────────────────────────────────────────

class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True)
    device_id    = Column(String(80), unique=True, nullable=False, index=True)
    zone_id      = Column(Integer, ForeignKey("zones.id",    ondelete="CASCADE"), nullable=False)
    network_id   = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    subline_name = Column(String(100))
    sensor_type  = Column(String(10), nullable=False, default="outlet")
    status       = Column(String(20), nullable=False, default="active")
    valve_state  = Column(String(10), nullable=False, default="open")
    last_seen    = Column(DateTime(timezone=True), nullable=True)
    installed_at = Column(DateTime(timezone=True), server_default=func.now())

    zone            = relationship("Zone",         back_populates="devices")
    network         = relationship("Network")
    readings        = relationship("Reading",      back_populates="device", cascade="all, delete-orphan")
    events          = relationship("Event",        back_populates="device", cascade="all, delete-orphan")
    valve_logs      = relationship("ValveLog",     back_populates="device", cascade="all, delete-orphan")
    daily_summaries = relationship("DailySummary", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_devices_network_zone", "network_id", "zone_id"),
    )


# ─────────────────────────────────────────────────────────────
#  READING
# ─────────────────────────────────────────────────────────────

class Reading(Base):
    __tablename__ = "readings"

    id           = Column(BigInteger, primary_key=True)
    device_id    = Column(String(80), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    network_id   = Column(String(80), nullable=False)
    zone_id      = Column(String(80), nullable=False)
    sensor_type  = Column(String(10), nullable=False)
    flow_rate    = Column(Numeric(10, 4), nullable=False)
    total_volume = Column(Numeric(14, 4), nullable=False)
    valve_status = Column(String(10),    nullable=False)
    timestamp    = Column(DateTime(timezone=True), nullable=False)
    received_at  = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="readings")

    __table_args__ = (
        UniqueConstraint("device_id", "timestamp", name="uq_reading_device_ts"),
        Index("ix_readings_device_ts_desc",  "device_id", "timestamp"),
        Index("ix_readings_network_zone_ts", "network_id", "zone_id", "timestamp"),
        Index(
            "ix_readings_outlet_partial",
            "device_id", "timestamp",
            postgresql_where="sensor_type = 'outlet'",
        ),
    )


# ─────────────────────────────────────────────────────────────
#  DAILY SUMMARY
# ─────────────────────────────────────────────────────────────

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id                  = Column(Integer, primary_key=True)
    device_id           = Column(String(80), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    network_id          = Column(String(80), nullable=False)
    zone_id             = Column(String(80), nullable=False)
    zone_type           = Column(String(50), nullable=False, default="general")
    sensor_type         = Column(String(10), nullable=False, default="outlet")
    summary_date        = Column(Date, nullable=False)
    total_volume_litres = Column(Numeric(14, 4), default=0)
    avg_flow_rate       = Column(Numeric(10, 4))
    max_flow_rate       = Column(Numeric(10, 4))
    min_flow_rate       = Column(Numeric(10, 4))
    reading_count       = Column(Integer, default=0)
    leak_event_count    = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(),
                                 onupdate=func.now())

    device = relationship("Device", back_populates="daily_summaries")

    __table_args__ = (
        UniqueConstraint("device_id", "summary_date", "sensor_type", name="uq_daily_summary"),
        Index("ix_daily_device_date",       "device_id",  "summary_date"),
        Index("ix_daily_network_zone_date", "network_id", "zone_id",   "summary_date"),
        Index("ix_daily_network_type_date", "network_id", "zone_type", "summary_date"),
    )


# ─────────────────────────────────────────────────────────────
#  EVENT
# ─────────────────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id          = Column(Integer, primary_key=True)
    device_id   = Column(String(80), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    network_id  = Column(Integer, ForeignKey("networks.id", ondelete="SET NULL"), nullable=True)
    zone_id     = Column(Integer, ForeignKey("zones.id",    ondelete="SET NULL"), nullable=True)
    event_type  = Column(String(40), nullable=False)
    severity    = Column(String(10), default="medium", nullable=False)
    description = Column(Text)
    resolved    = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    timestamp   = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="events")

    __table_args__ = (
        Index(
            "ix_events_unresolved_leaks",
            "device_id", "timestamp",
            postgresql_where="event_type = 'leak_detected' AND resolved = false",
        ),
        Index("ix_events_device_ts", "device_id", "timestamp"),
    )


# ─────────────────────────────────────────────────────────────
#  VALVE LOG
# ─────────────────────────────────────────────────────────────

class ValveLog(Base):
    __tablename__ = "valve_logs"

    id              = Column(Integer, primary_key=True)
    device_id       = Column(String(80), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    commanded_by    = Column(Integer,    ForeignKey("users.id",           ondelete="SET NULL"), nullable=True)
    action          = Column(String(10), nullable=False)
    source          = Column(String(20), default="manual", nullable=False)
    commanded_at    = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", back_populates="valve_logs")

    __table_args__ = (
        Index("ix_valve_logs_device_ts", "device_id", "commanded_at"),
    )