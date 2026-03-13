# app/routers/devices_router.py
# Network + Device management

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from auth import get_current_user
from models import User, Network, Zone, Device, Reading, ValveLog, Event
import asyncio
from mqtt_service import invalidate_device_cache


router = APIRouter(tags=["devices"])

# Shared MQTT publish queue (set by main.py)
_publish_queue: Optional[asyncio.Queue] = None
def set_publish_queue(q: asyncio.Queue):
    global _publish_queue
    _publish_queue = q


# ── Networks ───────────────────────────────────────────────────────────────────
class NetworkCreate(BaseModel):
    name: str
    location: Optional[str] = None


@router.post("/networks", status_code=201)
async def create_network(
    body: NetworkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    net = Network(name=body.name, location=body.location, owner_id=current_user.id)
    db.add(net)
    await db.commit()
    await db.refresh(net)
    return {"id": net.id, "name": net.name, "location": net.location}


@router.get("/networks")
async def list_networks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Network).where(Network.owner_id == current_user.id))
    return [{"id": n.id, "name": n.name, "location": n.location} for n in result.scalars()]


# ── Devices ────────────────────────────────────────────────────────────────────
class DeviceCreate(BaseModel):
    device_id: str
    zone_id:      int
    subline_name: Optional[str] = None
    sensor_type:  str = "outlet"   # "inlet" | "outlet"


@router.post("/networks/{network_id}/devices", status_code=201)
async def register_device(
    network_id: int,
    body: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.sensor_type not in ("inlet", "outlet"):
        raise HTTPException(status_code=400, detail="sensor_type must be 'inlet' or 'outlet'")

    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    existing = await db.execute(select(Device).where(Device.device_id == body.device_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Device ID already registered")

    device = Device(
        network_id=network_id,
        zone_id=body.zone_id,
        device_id=body.device_id,
        subline_name=body.subline_name,
        sensor_type=body.sensor_type,
    )
    db.add(device)
    await db.commit()
    invalidate_device_cache(body.device_id)
    await db.refresh(device)
    return {
        "id": device.id,
        "device_id": device.device_id,
        "sensor_type": device.sensor_type,
        "valve_state": device.valve_state,
    }


@router.get("/networks/{network_id}/devices")
async def list_devices(
    network_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    result = await db.execute(select(Device).where(Device.network_id == network_id))
    return [
        {
            "device_id": d.device_id,
            "subline_name": d.subline_name,
            "status": d.status,
            "valve_state": d.valve_state,
        }
        for d in result.scalars()
    ]


# ── Valve control ──────────────────────────────────────────────────────────────
class ValveCommand(BaseModel):
    action: str   # 'open' | 'close'


@router.post("/devices/{device_id}/valve")
async def control_valve(
    device_id: str,
    body: ValveCommand,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.action not in ("open", "close"):
        raise HTTPException(status_code=400, detail="action must be 'open' or 'close'")

    result = await db.execute(
        select(Device)
        .join(Network, Device.network_id == Network.id)
        .where(Device.device_id == device_id, Network.owner_id == current_user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.valve_state = body.action
    log = ValveLog(
        device_id=device_id,
        commanded_by=current_user.id,
        action=body.action,
        source="manual",
    )
    db.add(log)

    # Also create an event for audit trail
    event = Event(
        device_id=device_id,
        network_id=device.network_id,
        event_type=f"valve_{body.action}d",
        severity="low",
        description=f"Valve manually {body.action}d by user {current_user.id}.",
    )
    db.add(event)
    await db.commit()
    await db.refresh(log)

    if _publish_queue:
        await _publish_queue.put((device_id, body.action))

    return {"detail": f"Valve {body.action} command sent", "log_id": log.id}


@router.get("/devices/{device_id}/valve/logs")
async def valve_logs(
    device_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Device)
        .join(Network, Device.network_id == Network.id)
        .where(Device.device_id == device_id, Network.owner_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Device not found")

    logs = await db.execute(
        select(ValveLog)
        .where(ValveLog.device_id == device_id)
        .order_by(ValveLog.commanded_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": l.id,
            "action": l.action,
            "source": l.source,
            "commanded_by": l.commanded_by,
            "commanded_at": l.commanded_at.isoformat(),
            "acknowledged_at": l.acknowledged_at.isoformat() if l.acknowledged_at else None,
        }
        for l in logs.scalars()
    ]


# ── Zone flow status ───────────────────────────────────────────────────────────

@router.get("/zones/{zone_id}/flow-status")
async def zone_flow_status(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the latest inlet and outlet flow rates for a zone,
    plus the zone's valve state (open if ANY outlet device is open).
    Powers the Flutter Leakage page zone card.

    leak = (inFlow - outFlow) >= 0.1 AND valve_state == 'open'
    """
    # Ownership check: zone must belong to a network owned by current_user
    zone_result = await db.execute(
        select(Zone)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.id == zone_id, Network.owner_id == current_user.id)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    # Fetch latest reading per sensor_type using a subquery on timestamp
    from sqlalchemy import case as sa_case, literal_column

    # Get the most recent reading for each sensor_type in this zone
    inlet_result = await db.execute(
        select(Reading.flow_rate)
        .join(Device, Reading.device_id == Device.device_id)
        .where(Device.zone_id == zone_id, Reading.sensor_type == "inlet")
        .order_by(Reading.timestamp.desc())
        .limit(1)
    )
    outlet_result = await db.execute(
        select(Reading.flow_rate, Device.valve_state)
        .join(Device, Reading.device_id == Device.device_id)
        .where(Device.zone_id == zone_id, Reading.sensor_type == "outlet")
        .order_by(Reading.timestamp.desc())
        .limit(1)
    )

    inlet_row  = inlet_result.one_or_none()
    outlet_row = outlet_result.one_or_none()

    in_flow    = float(inlet_row.flow_rate)  if inlet_row  else 0.0
    out_flow   = float(outlet_row.flow_rate) if outlet_row else 0.0
    valve_state = outlet_row.valve_state     if outlet_row else "unknown"

    leak = (in_flow - out_flow) >= 0.1 and valve_state == "open"

    return {
        "zone_id":     zone_id,
        "zone":        zone.zone_name,
        "inFlow":      round(in_flow, 4),
        "outFlow":     round(out_flow, 4),
        "valve_state": valve_state,
        "leak":        leak,
    }


@router.get("/networks/{network_id}/zones/flow-status")
async def network_zones_flow_status(
    network_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns flow status for ALL zones in a network.
    Powers the Flutter Leakage page zone list.

    leak = (inFlow - outFlow) >= 0.1 AND valve_state == 'open'
    """
    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    zones_result = await db.execute(
        select(Zone).where(Zone.network_id == network_id)
    )
    zones = zones_result.scalars().all()

    output = []
    for zone in zones:
        inlet_result = await db.execute(
            select(Reading.flow_rate)
            .join(Device, Reading.device_id == Device.device_id)
            .where(Device.zone_id == zone.id, Reading.sensor_type == "inlet")
            .order_by(Reading.timestamp.desc())
            .limit(1)
        )
        outlet_result = await db.execute(
            select(Reading.flow_rate, Device.valve_state)
            .join(Device, Reading.device_id == Device.device_id)
            .where(Device.zone_id == zone.id, Reading.sensor_type == "outlet")
            .order_by(Reading.timestamp.desc())
            .limit(1)
        )
        inlet_row  = inlet_result.one_or_none()
        outlet_row = outlet_result.one_or_none()

        in_flow    = float(inlet_row.flow_rate)  if inlet_row  else 0.0
        out_flow   = float(outlet_row.flow_rate) if outlet_row else 0.0
        valve_state = outlet_row.valve_state     if outlet_row else "unknown"
        leak = (in_flow - out_flow) >= 0.1 and valve_state == "open"

        output.append({
            "zone_id":     zone.id,
            "zone":        zone.zone_name,
            "inFlow":      round(in_flow, 4),
            "outFlow":     round(out_flow, 4),
            "valve_state": valve_state,
            "leak":        leak,
        })

    return output
@router.patch("/events/{event_id}/resolve")
async def resolve_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    result = await db.execute(
        select(Event)
        .join(Device, Event.device_id == Device.device_id)
        .join(Network, Device.network_id == Network.id)
        .where(Event.id == event_id, Network.owner_id == current_user.id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.resolved = True
    event.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"detail": "Event resolved", "event_id": event_id}