# provisioning_router.py
# AquaSense — Device provisioning endpoint
# Called by Flutter during SoftAP device setup.
# Generates a device_id and returns MQTT + network credentials
# for the app to forward directly to the ESP32 over the local AP network.

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth import get_current_user
from config import settings
from database import get_db
from models import User, Network, Zone, Device

router = APIRouter(prefix="/provisioning", tags=["Provisioning"])


class ProvisionRequestSchema(BaseModel):
    network_id:  str   # slug e.g. "home_01"
    zone_id:     str   # slug e.g. "bathroom_01"
    sensor_type: str   # "inlet" or "outlet"
    chip_id:     str   # from ESP32 /info response

    @field_validator("sensor_type")
    @classmethod
    def validate_sensor_type(cls, v):
        if v not in ("inlet", "outlet"):
            raise ValueError("sensor_type must be 'inlet' or 'outlet'")
        return v

    @field_validator("chip_id")
    @classmethod
    def validate_chip_id(cls, v):
        v = v.strip().lower()
        if len(v) < 4:
            raise ValueError("chip_id too short")
        if len(v) > 20:
            raise ValueError("chip_id too long")
        return v

    @field_validator("network_id", "zone_id")
    @classmethod
    def validate_slugs(cls, v):
        v = v.strip()
        if len(v) == 0:
            raise ValueError("Cannot be empty")
        if len(v) > 80:
            raise ValueError("Too long")
        return v


@router.post("/generate-config")
async def generate_config(
    data:         ProvisionRequestSchema,
    current_user: User = Depends(get_current_user),
    db:           AsyncSession = Depends(get_db),
):
    # ── Verify network + zone belong to this user ──────────────────────
    result = await db.execute(
        select(Network, Zone)
        .join(Zone, Zone.network_id == Network.id)
        .where(
            Network.network_id == data.network_id,
            Zone.zone_id       == data.zone_id,
            Network.owner_id   == current_user.id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Network or zone not found, or does not belong to your account.",
        )

    network, zone = row

    # ── Build device_id — deterministic from chip_id + sensor_type ────
    # Format: pipe_{chip_suffix}_{sensor_type}
    # e.g. chip_id="a1b2c3d4" → "pipe_c3d4_inlet"
    chip_suffix = data.chip_id[-4:]
    device_id   = f"pipe_{chip_suffix}_{data.sensor_type}"

    # ── For inlet: also return the expected outlet device_id ───────────
    # The inlet firmware needs to subscribe to the outlet's MQTT topics.
    # We derive the outlet_device_id using the same chip_suffix convention.
    # If the outlet is provisioned separately with a different chip_id,
    # the user will need to re-provision the inlet — acceptable for v1.
    outlet_device_id = f"pipe_{chip_suffix}_outlet"

    return {
        "device_id":        device_id,
        "outlet_device_id": outlet_device_id,   # inlet uses this to subscribe to outlet topics
        "network_id":       data.network_id,
        "zone_id":          data.zone_id,
        "sensor_type":      data.sensor_type,
        "mqtt_broker_host": settings.MQTT_BROKER_HOST,
        "mqtt_broker_port": settings.MQTT_BROKER_PORT,
        "mqtt_username":    settings.MQTT_USERNAME,
        "mqtt_password":    settings.MQTT_PASSWORD,
    }