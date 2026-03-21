# device_router.py
# AquaSense v3.1 — Network, Zone, and Device management
#
# Changes from v3:
#   • NetworkCreate now requires network_id slug
#   • ZoneCreate added with zone_type and floor
#   • POST /networks/{id}/zones  — create zone
#   • GET  /networks/{id}/zones  — list zones (optional ?zone_type= filter)
#   • control_valve now publishes 4-tuple (not 2-tuple) to use hierarchical topic
#   • zone_flow_status includes zone_type and floor in response
#   • network_zones_flow_status ordered by zone_type, zone_id

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from database import get_db
from auth import get_current_user as _iot_dep
from models import User, Network, Zone, Device, Reading, ValveLog, Event
from mqtt_service import invalidate_device_cache

router = APIRouter(tags=["devices"])

_publish_queue: Optional[asyncio.Queue] = None

def set_publish_queue(q: asyncio.Queue):
    global _publish_queue
    _publish_queue = q


# ─────────────────────────────────────────────────────────────────────────────
#  NETWORKS
# ─────────────────────────────────────────────────────────────────────────────

class NetworkCreate(BaseModel):
    name:       str
    network_id: str              # MQTT slug e.g. "home_01"
    location:   Optional[str] = None


@router.post("/networks", status_code=201)
async def create_network(
    body:         NetworkCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    if not body.network_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="network_id must contain only letters, numbers, underscores, or hyphens"
        )
    existing = await db.execute(
        select(Network).where(Network.network_id == body.network_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="network_id already exists")

    net = Network(
        name       = body.name,
        network_id = body.network_id,
        location   = body.location,
        owner_id   = current_user.id,
    )
    db.add(net)
    await db.commit()
    await db.refresh(net)
    return {"id": net.id, "network_id": net.network_id, "name": net.name, "location": net.location}


@router.get("/networks")
async def list_networks(
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    result = await db.execute(select(Network).where(Network.owner_id == current_user.id))
    return [
        {"id": n.id, "network_id": n.network_id, "name": n.name, "location": n.location}
        for n in result.scalars()
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  ZONES
# ─────────────────────────────────────────────────────────────────────────────

class ZoneCreate(BaseModel):
    zone_id:   str               # MQTT slug e.g. "bathroom_01"
    zone_name: str               # Display name e.g. "Bathroom 01"
    zone_type: str               # Category: "bathroom"|"kitchen"|"outdoor"|"general"
    floor:     Optional[str] = None


@router.post("/networks/{network_id}/zones", status_code=201)
async def create_zone(
    network_id:   int,
    body:         ZoneCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    existing = await db.execute(
        select(Zone).where(Zone.network_id == network_id, Zone.zone_id == body.zone_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="zone_id already exists in this network")

    zone = Zone(
        zone_id    = body.zone_id,
        zone_name  = body.zone_name,
        zone_type  = body.zone_type,
        floor      = body.floor,
        network_id = network_id,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return {
        "id":        zone.id,
        "zone_id":   zone.zone_id,
        "zone_name": zone.zone_name,
        "zone_type": zone.zone_type,
        "floor":     zone.floor,
    }


@router.get("/networks/{network_id}/zones")
async def list_zones(
    network_id:   int,
    zone_type:    Optional[str] = None,
    db:           AsyncSession  = Depends(get_db),
    current_user: User          = Depends(_iot_dep),
):
    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    query = select(Zone).where(Zone.network_id == network_id)
    if zone_type:
        query = query.where(Zone.zone_type == zone_type)
    query = query.order_by(Zone.zone_type, Zone.zone_id)

    result = await db.execute(query)
    return [
        {"id": z.id, "zone_id": z.zone_id, "zone_name": z.zone_name,
         "zone_type": z.zone_type, "floor": z.floor}
        for z in result.scalars()
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  DEVICES
# ─────────────────────────────────────────────────────────────────────────────

class DeviceCreate(BaseModel):
    device_id:    str
    zone_id:      int
    subline_name: Optional[str] = None
    sensor_type:  str = "outlet"


@router.post("/networks/{network_id}/devices", status_code=201)
async def register_device(
    network_id:   int,
    body:         DeviceCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    if body.sensor_type not in ("inlet", "outlet"):
        raise HTTPException(status_code=400, detail="sensor_type must be 'inlet' or 'outlet'")

    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    zone_result = await db.execute(
        select(Zone).where(Zone.id == body.zone_id, Zone.network_id == network_id)
    )
    if not zone_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Zone not found in this network")

    existing = await db.execute(select(Device).where(Device.device_id == body.device_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Device ID already registered")

    device = Device(
        network_id   = network_id,
        zone_id      = body.zone_id,
        device_id    = body.device_id,
        subline_name = body.subline_name,
        sensor_type  = body.sensor_type,
    )
    db.add(device)
    await db.commit()
    invalidate_device_cache(body.device_id)
    await db.refresh(device)
    return {
        "id":          device.id,
        "device_id":   device.device_id,
        "sensor_type": device.sensor_type,
        "valve_state": device.valve_state,
    }


@router.get("/networks/{network_id}/devices")
async def list_devices(
    network_id:   int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    result = await db.execute(
        select(Device)
        .join(Zone, Device.zone_id == Zone.id)
        .where(Device.network_id == network_id)
        .order_by(Zone.zone_id, Device.device_id)
    )
    return [
        {
            "device_id":    d.device_id,
            "subline_name": d.subline_name,
            "sensor_type":  d.sensor_type,
            "status":       d.status,
            "valve_state":  d.valve_state,
            "last_seen":    d.last_seen.isoformat() if d.last_seen else None,
        }
        for d in result.scalars()
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  VALVE CONTROL
# ─────────────────────────────────────────────────────────────────────────────

class ValveCommand(BaseModel):
    action: str   # "open" | "close"


@router.post("/devices/{device_id}/valve")
async def control_valve(
    device_id:    str,
    body:         ValveCommand,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
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

    # Fetch zone and network slugs needed for the hierarchical MQTT topic
    zone_net_result = await db.execute(
        select(Zone.zone_id, Network.network_id)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.id == device.zone_id)
    )
    zone_net = zone_net_result.one_or_none()
    if not zone_net:
        raise HTTPException(status_code=500, detail="Zone/network lookup failed")

    zone_slug, network_slug = zone_net.zone_id, zone_net.network_id

    device.valve_state = body.action
    log = ValveLog(
        device_id    = device_id,
        commanded_by = current_user.id,
        action       = body.action,
        source       = "manual",
    )
    db.add(log)
    db.add(Event(
        device_id   = device_id,
        network_id  = device.network_id,
        zone_id     = device.zone_id,
        event_type  = f"valve_{body.action}d",
        severity    = "low",
        description = f"Valve manually {body.action}d by user {current_user.id}.",
    ))
    await db.commit()
    await db.refresh(log)

    if _publish_queue:
        # 4-tuple so mqtt_service builds: aquasense/{network}/{zone}/{device}/valve
        await _publish_queue.put((network_slug, zone_slug, device_id, body.action))

    return {"detail": f"Valve {body.action} command sent", "log_id": log.id}


@router.get("/devices/{device_id}/valve/logs")
async def valve_logs(
    device_id:    str,
    limit:        int          = 50,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
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
            "id":              l.id,
            "action":          l.action,
            "source":          l.source,
            "commanded_by":    l.commanded_by,
            "commanded_at":    l.commanded_at.isoformat(),
            "acknowledged_at": l.acknowledged_at.isoformat() if l.acknowledged_at else None,
        }
        for l in logs.scalars()
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  ZONE FLOW STATUS  (Leakages screen)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/zones/{zone_id}/flow-status")
async def zone_flow_status(
    zone_id:      int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    zone_result = await db.execute(
        select(Zone)
        .join(Network, Zone.network_id == Network.id)
        .where(Zone.id == zone_id, Network.owner_id == current_user.id)
    )
    zone = zone_result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

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
    inlet_row   = inlet_result.one_or_none()
    outlet_row  = outlet_result.one_or_none()
    in_flow     = float(inlet_row.flow_rate)  if inlet_row  else 0.0
    out_flow    = float(outlet_row.flow_rate) if outlet_row else 0.0
    valve_state = outlet_row.valve_state      if outlet_row else "unknown"
    leak        = (in_flow - out_flow) >= 0.1 and valve_state == "open"

    return {
        "zone_id":     zone_id,
        "zone_slug":   zone.zone_id,
        "zone_name":   zone.zone_name,
        "zone_type":   zone.zone_type,    # ← NEW
        "floor":       zone.floor,         # ← NEW
        "inFlow":      round(in_flow,  4),
        "outFlow":     round(out_flow, 4),
        "valve_state": valve_state,
        "leak":        leak,
    }


@router.get("/networks/{network_id}/zones/flow-status")
async def network_zones_flow_status(
    network_id:   int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    """
    All zones flow status — powers the Leakages page zone list.
    Ordered by zone_type then zone_id so Flutter renders consistent card order.
    """
    net_result = await db.execute(
        select(Network).where(Network.id == network_id, Network.owner_id == current_user.id)
    )
    if not net_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Network not found")

    zones_result = await db.execute(
        select(Zone)
        .where(Zone.network_id == network_id)
        .order_by(Zone.zone_type, Zone.zone_id)    # ← consistent order
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
        inlet_row   = inlet_result.one_or_none()
        outlet_row  = outlet_result.one_or_none()
        in_flow     = float(inlet_row.flow_rate)  if inlet_row  else 0.0
        out_flow    = float(outlet_row.flow_rate) if outlet_row else 0.0
        valve_state = outlet_row.valve_state      if outlet_row else "unknown"
        leak        = (in_flow - out_flow) >= 0.1 and valve_state == "open"

        output.append({
            "zone_id":     zone.id,
            "zone_slug":   zone.zone_id,
            "zone_name":   zone.zone_name,
            "zone_type":   zone.zone_type,    # ← NEW
            "floor":       zone.floor,         # ← NEW
            "inFlow":      round(in_flow,  4),
            "outFlow":     round(out_flow, 4),
            "valve_state": valve_state,
            "leak":        leak,
        })

    return output


# ─────────────────────────────────────────────────────────────────────────────
#  EVENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/events/{event_id}/resolve")
async def resolve_event(
    event_id:     int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(_iot_dep),
):
    result = await db.execute(
        select(Event)
        .join(Device,  Event.device_id   == Device.device_id)
        .join(Network, Device.network_id == Network.id)
        .where(Event.id == event_id, Network.owner_id == current_user.id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.resolved    = True
    event.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"detail": "Event resolved", "event_id": event_id}