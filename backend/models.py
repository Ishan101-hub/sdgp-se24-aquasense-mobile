# models.py
# AquaSense v3 — SQLAlchemy ORM Models
#
# Hierarchy:  User → Network → Zone → Device → Reading
#
# Key changes from v2:
#   • Zone model added  (id, zone_id, zone_name, network_id)
#   • Device gains zone_id FK + last_seen heartbeat column
#   • Reading gains network_id, zone_id, sensor_type columns
#   • Event  gains zone_id column
#   • DailySummary gains network_id, zone_id, sensor_type columns
#   • All performance indexes defined inside __table_args__
#     so SQLAlchemy / Alembic manages them — no raw SQL needed

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

    networks       = relationship("Network",      back_populates="owner",   cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user",    cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text,    unique=True, nullable=False)
    issued_at  = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


# ─────────────────────────────────────────────────────────────
#  NETWORK
#  One network = one building / house / site
#  MQTT prefix: aquasense/{network_id}/...
# ─────────────────────────────────────────────────────────────

class Network(Base):
    __tablename__ = "networks"

    id         = Column(Integer, primary_key=True)
    # Human-readable slug used in MQTT topics (e.g. "building_a")
    network_id = Column(String(80), unique=True, nullable=False, index=True)
    name       = Column(String(100), nullable=False)
    location   = Column(String(200))
    owner_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner   = relationship("User",    back_populates="networks")
    zones   = relationship("Zone",    back_populates="network", cascade="all, delete-orphan")


# ─────────────────────────────────────────────────────────────
#  ZONE
#  One zone = one location inside a network (bathroom_01, kitchen_01)
#  MQTT prefix: aquasense/{network_id}/{zone_id}/...
# ─────────────────────────────────────────────────────────────

class Zone(Base):
    __tablename__ = "zones"

    id         = Column(Integer, primary_key=True)
    # Human-readable slug used in MQTT topics (e.g. "bathroom_01")
    zone_id    = Column(String(80), nullable=False, index=True)
    zone_name  = Column(String(100), nullable=False)
    network_id = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    network = relationship("Network", back_populates="zones")
    devices = relationship("Device",  back_populates="zone",    cascade="all, delete-orphan")

    __table_args__ = (
        # zone_id is unique within a network (not globally)
        UniqueConstraint("network_id", "zone_id", name="uq_zone_per_network"),
        # Fast lookup for MQTT topic parsing: WHERE network_id=? AND zone_id=?
        Index("ix_zones_network_zone", "network_id", "zone_id"),
    )


# ─────────────────────────────────────────────────────────────
#  DEVICE
#  One device = one physical ESP32 node (inlet or outlet)
#  MQTT prefix: aquasense/{network_id}/{zone_id}/{device_id}/...
# ─────────────────────────────────────────────────────────────

class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True)
    # String ID that matches the MQTT topic segment exactly
    device_id    = Column(String(80), unique=True, nullable=False, index=True)
    zone_id      = Column(Integer, ForeignKey("zones.id",    ondelete="CASCADE"), nullable=False)
    network_id   = Column(Integer, ForeignKey("networks.id", ondelete="CASCADE"), nullable=False)
    subline_name = Column(String(100))          # friendly label, e.g. "Kitchen Inlet"
    sensor_type  = Column(String(10), nullable=False, default="outlet")  # "inlet" | "outlet"
    status       = Column(String(20), nullable=False, default="active")  # "active" | "inactive"
    valve_state  = Column(String(10), nullable=False, default="open")    # "open"  | "closed"
    last_seen    = Column(DateTime(timezone=True), nullable=True)        # updated on each reading
    installed_at = Column(DateTime(timezone=True), server_default=func.now())

    zone            = relationship("Zone",         back_populates="devices")
    network         = relationship("Network")
    readings        = relationship("Reading",      back_populates="device", cascade="all, delete-orphan")
    events          = relationship("Event",        back_populates="device", cascade="all, delete-orphan")
    valve_logs      = relationship("ValveLog",     back_populates="device", cascade="all, delete-orphan")
    daily_summaries = relationship("DailySummary", back_populates="device", cascade="all, delete-orphan")

    __table_args__ = (
        # Quickly find all devices in a zone for MQTT topic validation
        Index("ix_devices_network_zone", "network_id", "zone_id"),
    )


# ─────────────────────────────────────────────────────────────
#  READING
#  Only outlet readings are stored (inlet handles leak locally).
#  network_id + zone_id are denormalised here so analytics queries
#  never need to join back through Device → Zone → Network.
# ─────────────────────────────────────────────────────────────

class Reading(Base):
    __tablename__ = "readings"

    id          = Column(BigInteger, primary_key=True)
    device_id   = Column(String(80), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    network_id  = Column(String(80), nullable=False)   # denormalised MQTT string, e.g. "building_a"
    zone_id     = Column(String(80), nullable=False)   # denormalised MQTT string, e.g. "kitchen_01"
    sensor_type = Column(String(10), nullable=False)   # "inlet" | "outlet"
    flow_rate   = Column(Numeric(10, 4), nullable=False)
    total_volume= Column(Numeric(14, 4), nullable=False)
    valve_status= Column(String(10),    nullable=False)
    timestamp   = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="readings")

    __table_args__ = (
        # Primary dedup constraint
        UniqueConstraint("device_id", "timestamp", name="uq_reading_device_ts"),

        # ── Performance indexes ──────────────────────────────────────────────

        # 1. Hottest query: latest N readings for one device (live graph, dashboard)
        #    SELECT … WHERE device_id=? ORDER BY timestamp DESC LIMIT ?
        Index("ix_readings_device_ts_desc", "device_id", "timestamp"),

        # 2. Zone-level analytics: all readings in a zone for a time window
        #    SELECT … WHERE network_id=? AND zone_id=? AND timestamp BETWEEN …
        Index("ix_readings_network_zone_ts", "network_id", "zone_id", "timestamp"),

        # 3. Outlet-only scan (most analytics only want outlet sensor_type)
        #    Partial index — only indexes rows WHERE sensor_type = 'outlet'
        #    SQLAlchemy supports postgresql_where for partial indexes
        Index(
            "ix_readings_outlet_partial",
            "device_id", "timestamp",
            postgresql_where="sensor_type = 'outlet'",
        ),
    )


# ─────────────────────────────────────────────────────────────
#  DAILY SUMMARY
#  Pre-aggregated nightly. All monthly/annual analytics read
#  from here — never from the raw readings table.
# ─────────────────────────────────────────────────────────────

class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id                  = Column(Integer, primary_key=True)
    device_id           = Column(String(80), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    network_id          = Column(String(80), nullable=False)  # denormalised for zone/network queries
    zone_id             = Column(String(80), nullable=False)  # denormalised
    sensor_type         = Column(String(10), nullable=False, default="outlet")
    summary_date        = Column(Date,       nullable=False)
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

        # 4. Device monthly report: WHERE device_id=? AND summary_date BETWEEN …
        Index("ix_daily_device_date", "device_id", "summary_date"),

        # 5. Zone monthly aggregation: WHERE network_id=? AND zone_id=? AND date range
        Index("ix_daily_network_zone_date", "network_id", "zone_id", "summary_date"),
    )


# ─────────────────────────────────────────────────────────────
#  EVENT  (leak_detected, valve_opened, valve_closed, etc.)
# ─────────────────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id          = Column(Integer, primary_key=True)
    device_id   = Column(String(80), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    network_id  = Column(Integer,   ForeignKey("networks.id", ondelete="SET NULL"), nullable=True)
    zone_id     = Column(Integer,   ForeignKey("zones.id",    ondelete="SET NULL"), nullable=True)
    event_type  = Column(String(40), nullable=False)
    severity    = Column(String(10), default="medium", nullable=False)
    description = Column(Text)
    resolved    = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    timestamp   = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="events")

    __table_args__ = (
        # 6. Partial index — only unresolved leak events
        #    Alerts screen: WHERE device_id=? AND event_type='leak_detected' AND resolved=false
        Index(
            "ix_events_unresolved_leaks",
            "device_id", "timestamp",
            postgresql_where="event_type = 'leak_detected' AND resolved = false",
        ),
        # Full event log by device
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
    action          = Column(String(10), nullable=False)          # "open" | "close"
    source          = Column(String(20), default="manual", nullable=False)  # "manual" | "auto_leak"
    commanded_at    = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    device = relationship("Device", back_populates="valve_logs")

    __table_args__ = (
        Index("ix_valve_logs_device_ts", "device_id", "commanded_at"),
    )