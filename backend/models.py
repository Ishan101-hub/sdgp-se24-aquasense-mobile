# models.py
# AquaSense v3.1 — SQLAlchemy ORM Models
# Hierarchy: User → Network → Zone → Device → Reading
#
# Changes from v3:
#   • Zone gains zone_type and floor columns
#   • DailySummary gains zone_type (denormalised) column
#   • Two new indexes: ix_zones_network_zone_type, ix_daily_network_type_date

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
#  AUTH
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True)
    email         = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role          = Column(String(20), nullable=False, default="user")
    is_active     = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    networks       = relationship("Network",      back_populates="owner",  cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user",   cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, unique=True, nullable=False)
    issued_at  = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


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
#  zone_id   = MQTT slug, unique per network (e.g. "bathroom_01")
#  zone_type = category label (e.g. "bathroom", "kitchen", "outdoor")
#  floor     = optional floor label (e.g. "ground", "floor1", "floor2")
# ─────────────────────────────────────────────────────────────

class Zone(Base):
    __tablename__ = "zones"

    id         = Column(Integer, primary_key=True)
    zone_id    = Column(String(80), nullable=False, index=True)
    zone_name  = Column(String(100), nullable=False)
    zone_type  = Column(String(50), nullable=False, default="general")
    floor      = Column(String(50), nullable=True)
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    network = relationship("Network", back_populates="zones")
    devices = relationship("Device",  back_populates="zone", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("network_id", "zone_id", name="uq_zone_per_network"),
        # MQTT ingestion: WHERE network_id=? AND zone_id=? (called on every message)
        Index("ix_zones_network_zone",      "network_id", "zone_id"),
        # Optional type filter: GET /analytics/zones/summary?zone_type=bathroom
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
    zone_type           = Column(String(50), nullable=False, default="general")  # denormalised
    sensor_type         = Column(String(10), nullable=False, default="outlet")
    summary_date        = Column(Date, nullable=False)
    total_volume_litres = Column(Numeric(14, 4), default=0)
    avg_flow_rate       = Column(Numeric(10, 4))
    max_flow_rate       = Column(Numeric(10, 4))
    min_flow_rate       = Column(Numeric(10, 4))
    reading_count       = Column(Integer, default=0)
    leak_event_count    = Column(Integer, default=0)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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