# """
# AquaSense Leak Detection Service

# CRITICAL: This logic MUST match the ESP32 inlet device exactly.

# ESP32 Leak Detection Algorithm:
# 1. Check outlet device is alive (heartbeat < 5 sec)
# 2. Check valve is currently open
# 3. Check (inlet_flow - outlet_flow) > 0.8 L/min
# 4. Count consecutive seconds above threshold
# 5. If count >= 3: leak confirmed
# 6. Close valve, create alert, publish MQTT

# Server implements identical logic as BACKUP detection.
# The inlet ESP32 is the primary safety controller.
# The server is the monitoring and backup controller.
# """

# import logging
# from dataclasses import dataclass
# from datetime import datetime
# from typing import Dict, Optional, Callable, Awaitable

# from config import FLOW_MISMATCH_THRESHOLD_LPM, LEAK_CONFIRM_COUNT, HEARTBEAT_TIMEOUT_SEC
# from models import ValveState, EventType

# logger = logging.getLogger("aquasense.leak")

# # Minimum inlet flow that counts as "water is flowing" when valve is closed.
# # Anything below this is considered sensor noise and ignored.
# VALVE_FAILURE_MIN_FLOW_LPM: float = 0.5


# # ─────────────────────────────────────────────────────────────────────────────
# #  Zone runtime state
# # ─────────────────────────────────────────────────────────────────────────────

# @dataclass
# class ZoneState:
#     """
#     Runtime state for a single zone's leak detection.
#     Tracks the same state variables as the ESP32 inlet device.
#     """
#     zone_id: int

#     inlet_flow_lpm:  float = 0.0
#     outlet_flow_lpm: float = 0.0
#     inlet_timestamp:  Optional[datetime] = None
#     outlet_timestamp: Optional[datetime] = None

#     # Heartbeat tracking — matches ESP32: lastHeartbeatMillis
#     last_outlet_heartbeat: Optional[datetime] = None

#     # Valve state — kept in sync with Device.valve_state in DB
#     valve_state: ValveState = ValveState.UNKNOWN

#     # Leak confirmation counter — matches ESP32: leakConfirmCounter
#     flow_mismatch_counter: int = 0

#     is_leak_active:   bool = False
#     leak_detected_at: Optional[datetime] = None

#     # Valve failure tracking — flow detected while valve is closed
#     is_valve_failure_active:   bool = False
#     valve_failure_detected_at: Optional[datetime] = None


# # ─────────────────────────────────────────────────────────────────────────────
# #  Module-level singleton — created by main.py, used by routers
# # ─────────────────────────────────────────────────────────────────────────────

# _leak_service_instance: Optional["LeakDetectionService"] = None


# def get_leak_service() -> Optional["LeakDetectionService"]:
#     """Return the module-level instance. Used by routers that need to clear leak state."""
#     return _leak_service_instance


# def set_leak_service(svc: "LeakDetectionService") -> None:
#     global _leak_service_instance
#     _leak_service_instance = svc


# # ─────────────────────────────────────────────────────────────────────────────
# #  LeakDetectionService
# # ─────────────────────────────────────────────────────────────────────────────

# class LeakDetectionService:
#     """
#     Server-side leak detection that mirrors ESP32 inlet logic exactly.

#     DB writes and MQTT publishes are handled via injected callbacks so this
#     class stays pure and testable.
#     """

#     def __init__(
#         self,
#         on_leak_detected: Optional[Callable[[int, float, float], Awaitable[None]]] = None,
#         on_valve_command: Optional[Callable[[int, str], Awaitable[None]]] = None,
#         on_event_created: Optional[Callable[[int, EventType, str, dict], Awaitable[None]]] = None,
#     ):
#         self._zone_states: Dict[int, ZoneState] = {}
#         self._on_leak_detected = on_leak_detected
#         self._on_valve_command = on_valve_command
#         self._on_event_created = on_event_created

#         # MUST MATCH ESP32
#         self.threshold_lpm         = FLOW_MISMATCH_THRESHOLD_LPM
#         self.confirm_count         = LEAK_CONFIRM_COUNT
#         self.heartbeat_timeout_sec = HEARTBEAT_TIMEOUT_SEC

#         logger.info(
#             "LeakDetectionService ready — threshold=%.1f L/min  confirm=%d  heartbeat=%.0fs",
#             self.threshold_lpm, self.confirm_count, self.heartbeat_timeout_sec,
#         )

#     def _get_zone_state(self, zone_id: int) -> ZoneState:
#         if zone_id not in self._zone_states:
#             self._zone_states[zone_id] = ZoneState(zone_id=zone_id)
#         return self._zone_states[zone_id]

#     # ── Input handlers — called by mqtt_service ───────────────────────────────

#     async def update_inlet_flow(self, zone_id: int, flow_lpm: float) -> None:
#         """Update inlet flow and run leak evaluation. Called on every inlet reading."""
#         state = self._get_zone_state(zone_id)
#         state.inlet_flow_lpm  = flow_lpm
#         state.inlet_timestamp = datetime.utcnow()
#         logger.debug("Zone %d: inlet_flow = %.2f L/min", zone_id, flow_lpm)
#         await self._evaluate_leak_condition(zone_id)
#         await self._evaluate_valve_failure(zone_id)

#     async def update_outlet_flow(self, zone_id: int, flow_lpm: float) -> None:
#         """Update outlet flow. Called on every outlet reading."""
#         state = self._get_zone_state(zone_id)
#         state.outlet_flow_lpm  = flow_lpm
#         state.outlet_timestamp = datetime.utcnow()
#         logger.debug("Zone %d: outlet_flow = %.2f L/min", zone_id, flow_lpm)

#     async def update_outlet_heartbeat(self, zone_id: int) -> None:
#         """
#         Record outlet device is alive. Called on every heartbeat message.
#         Matches ESP32: lastHeartbeatMillis = millis();
#         """
#         state = self._get_zone_state(zone_id)
#         state.last_outlet_heartbeat = datetime.utcnow()
#         logger.debug("Zone %d: outlet heartbeat", zone_id)

#     async def update_valve_state(self, zone_id: int, valve_state: ValveState) -> None:
#         """Sync valve state from DB/device. Resets counter on any state change."""
#         state = self._get_zone_state(zone_id)
#         if state.valve_state != valve_state:
#             logger.info(
#                 "Zone %d: valve %s → %s",
#                 zone_id, state.valve_state.value, valve_state.value,
#             )
#             state.valve_state           = valve_state
#             state.flow_mismatch_counter = 0   # reset on valve change
#             # If valve just opened, clear any active valve failure — flow is now expected
#             if valve_state == ValveState.OPEN:
#                 state.is_valve_failure_active = False

#     # ── Core detection — MATCHES ESP32 EXACTLY ───────────────────────────────

#     async def _evaluate_leak_condition(self, zone_id: int) -> None:
#         """
#         Mirror of ESP32 checkLeakCondition() with server-side additions:

#         ```cpp
#         bool outletAlive = (millis() - lastHeartbeatMillis) < HEARTBEAT_TIMEOUT_MS;
#         if (!outletAlive) { leakConfirmCounter = 0; return; }
#         if (valveState != VALVE_OPEN) { leakConfirmCounter = 0; return; }
#         float delta = inletFlow - outletFlow;
#         if (delta > FLOW_DIFF_THRESHOLD) { leakConfirmCounter++; }
#         else { leakConfirmCounter = 0; }
#         if (leakConfirmCounter >= LEAK_CONFIRM_THRESHOLD) { onLeakDetected(); }
#         ```

#         Server addition (not in ESP32 — network latency means readings can arrive
#         out of sync): timestamp alignment check between inlet and outlet.
#         If the two readings are more than 2 seconds apart the delta is stale
#         and could produce a false leak, so the counter is reset.
#         """
#         state = self._get_zone_state(zone_id)

#         # STEP 1 — outlet alive?
#         if not self._is_outlet_alive(state):
#             if state.flow_mismatch_counter > 0:
#                 logger.debug("Zone %d: outlet offline — resetting counter", zone_id)
#             state.flow_mismatch_counter = 0
#             return

#         # STEP 2 — valve open?
#         if state.valve_state != ValveState.OPEN:
#             if state.flow_mismatch_counter > 0:
#                 logger.debug("Zone %d: valve not open — resetting counter", zone_id)
#             state.flow_mismatch_counter = 0
#             return

#         # STEP 3 — timestamp alignment check
#         # Inlet and outlet readings must be recent and within 2 seconds of each other.
#         # If they are misaligned (old outlet + new inlet, or vice versa), the delta
#         # is stale and would produce a false leak. Reset counter and skip.
#         if state.inlet_timestamp is None or state.outlet_timestamp is None:
#             logger.debug("Zone %d: missing timestamp — skipping evaluation", zone_id)
#             state.flow_mismatch_counter = 0
#             return

#         ts_gap = abs((state.inlet_timestamp - state.outlet_timestamp).total_seconds())
#         if ts_gap > 2.0:
#             if state.flow_mismatch_counter > 0:
#                 logger.debug(
#                     "Zone %d: timestamp gap=%.1fs > 2s — resetting counter",
#                     zone_id, ts_gap,
#                 )
#             state.flow_mismatch_counter = 0
#             return

#         # STEP 4 — flow delta
#         delta = state.inlet_flow_lpm - state.outlet_flow_lpm

#         # STEP 5 — confirmation counter
#         if delta > self.threshold_lpm:
#             state.flow_mismatch_counter += 1
#             logger.debug(
#                 "Zone %d: delta=%.2f L/min  counter=%d/%d",
#                 zone_id, delta, state.flow_mismatch_counter, self.confirm_count,
#             )
#         else:
#             if state.flow_mismatch_counter > 0:
#                 logger.debug("Zone %d: delta normalised — resetting counter", zone_id)
#             state.flow_mismatch_counter = 0

#         # STEP 6 — confirmed?
#         if state.flow_mismatch_counter >= self.confirm_count:
#             await self._on_leak_confirmed(zone_id, state)

#     def _is_outlet_alive(self, state: ZoneState) -> bool:
#         """Matches ESP32: bool outletAlive = (millis() - lastHeartbeatMillis) < HEARTBEAT_TIMEOUT_MS"""
#         if state.last_outlet_heartbeat is None:
#             return False
#         return (datetime.utcnow() - state.last_outlet_heartbeat).total_seconds() < self.heartbeat_timeout_sec

#     async def _on_leak_confirmed(self, zone_id: int, state: ZoneState) -> None:
#         """
#         Matches ESP32 onLeakDetected():
#             closeValve(); publishLeakAlert(); leakConfirmCounter = 0;
#         """
#         if state.is_leak_active:
#             return   # already active — don't spam

#         state.is_leak_active        = True
#         state.leak_detected_at      = datetime.utcnow()
#         state.flow_mismatch_counter = 0

#         delta = state.inlet_flow_lpm - state.outlet_flow_lpm

#         logger.warning(
#             "LEAK CONFIRMED zone=%d  inlet=%.2f  outlet=%.2f  delta=%.2f L/min",
#             zone_id, state.inlet_flow_lpm, state.outlet_flow_lpm, delta,
#         )

#         if self._on_event_created:
#             await self._on_event_created(
#                 zone_id,
#                 EventType.LEAK_DETECTED,
#                 f"Hidden leak: {delta:.2f} L/min lost between inlet and outlet",
#                 {
#                     "inlet_flow_lpm":  state.inlet_flow_lpm,
#                     "outlet_flow_lpm": state.outlet_flow_lpm,
#                     "delta_lpm":       delta,
#                     "threshold_lpm":   self.threshold_lpm,
#                     "confirm_count":   self.confirm_count,
#                     "source":          "server_backup",
#                 },
#             )

#         if self._on_valve_command:
#             await self._on_valve_command(zone_id, "close")

#         if self._on_leak_detected:
#             await self._on_leak_detected(zone_id, state.inlet_flow_lpm, state.outlet_flow_lpm)

#     # ── Valve failure detection ───────────────────────────────────────────────

#     async def _evaluate_valve_failure(self, zone_id: int) -> None:
#         """
#         Detect flow through a closed valve.

#         Conditions (all must be true):
#           • valve_state == CLOSED or UNKNOWN (not OPEN)
#           • inlet_flow > VALVE_FAILURE_MIN_FLOW_LPM
#           • Not already flagged as active

#         Possible causes:
#           • Valve stuck open or partially open
#           • Pipe bypass around the valve
#           • Leak upstream of the valve
#           • Valve hardware failure

#         This runs on every inlet reading alongside the normal leak check.
#         It does NOT close the valve (it's already supposed to be closed) —
#         it only creates a VALVE_FAILURE event for the mobile alert screen.
#         """
#         state = self._get_zone_state(zone_id)

#         # Only check when valve is closed or state unknown
#         if state.valve_state == ValveState.OPEN:
#             return

#         # Ignore sensor noise below minimum threshold
#         if state.inlet_flow_lpm <= VALVE_FAILURE_MIN_FLOW_LPM:
#             # Flow returned to zero — clear active flag so next incident re-fires
#             if state.is_valve_failure_active:
#                 logger.info(
#                     "Zone %d: valve failure cleared — flow dropped to %.2f L/min",
#                     zone_id, state.inlet_flow_lpm,
#                 )
#                 state.is_valve_failure_active = False
#             return

#         # Flow above threshold while valve is closed
#         if state.is_valve_failure_active:
#             return   # already flagged — don't spam

#         state.is_valve_failure_active   = True
#         state.valve_failure_detected_at = datetime.utcnow()

#         logger.warning(
#             "VALVE FAILURE zone=%d  valve=%s  inlet=%.2f L/min",
#             zone_id, state.valve_state.value, state.inlet_flow_lpm,
#         )

#         if self._on_event_created:
#             await self._on_event_created(
#                 zone_id,
#                 EventType.VALVE_FAILURE,
#                 (
#                     f"Flow detected with valve {state.valve_state.value}: "
#                     f"{state.inlet_flow_lpm:.2f} L/min. "
#                     f"Possible causes: valve stuck open, bypass pipe, or upstream leak."
#                 ),
#                 {
#                     "inlet_flow_lpm": state.inlet_flow_lpm,
#                     "valve_state":    state.valve_state.value,
#                     "threshold_lpm":  VALVE_FAILURE_MIN_FLOW_LPM,
#                 },
#             )

#     async def clear_valve_failure(self, zone_id: int) -> None:
#         """
#         Clear valve failure flag for a zone (called when user resolves the alert).
#         """
#         state = self._get_zone_state(zone_id)
#         if state.is_valve_failure_active:
#             state.is_valve_failure_active = False
#             logger.info("Zone %d: valve failure cleared by user", zone_id)

#     # ── Manual controls ───────────────────────────────────────────────────────

#     async def clear_leak(self, zone_id: int) -> None:
#         """
#         Clear leak flag when user resolves an alert.
#         Valve stays closed — user must open it explicitly.
#         """
#         state = self._get_zone_state(zone_id)
#         if not state.is_leak_active:
#             return

#         duration                    = self._get_leak_duration(state)
#         state.is_leak_active        = False
#         state.flow_mismatch_counter = 0

#         logger.info("Zone %d: leak cleared by user (duration=%.0fs)", zone_id, duration or 0)

#         if self._on_event_created:
#             await self._on_event_created(
#                 zone_id,
#                 EventType.LEAK_CLEARED,
#                 "Leak alert cleared by user",
#                 {"cleared_by": "user", "leak_duration_sec": duration},
#             )

#     def _get_leak_duration(self, state: ZoneState) -> Optional[float]:
#         if state.leak_detected_at:
#             return (datetime.utcnow() - state.leak_detected_at).total_seconds()
#         return None

#     # ── Status queries ────────────────────────────────────────────────────────

#     def get_zone_state(self, zone_id: int) -> Optional[ZoneState]:
#         return self._zone_states.get(zone_id)

#     def get_all_zone_states(self) -> Dict[int, ZoneState]:
#         return self._zone_states.copy()

#     def is_leak_active(self, zone_id: int) -> bool:
#         state = self._zone_states.get(zone_id)
#         return state.is_leak_active if state else False

#     def get_current_delta(self, zone_id: int) -> Optional[float]:
#         state = self._zone_states.get(zone_id)
#         if state and state.inlet_timestamp and state.outlet_timestamp:
#             return state.inlet_flow_lpm - state.outlet_flow_lpm
#         return None

"""
AquaSense Leak Detection Service

CRITICAL: This logic MUST match the ESP32 inlet device exactly.

ESP32 Leak Detection Algorithm:
1. Check outlet device is alive (heartbeat < 5 sec)
2. Check valve is currently open
3. Check (inlet_flow - outlet_flow) > 0.8 L/min
4. Count consecutive seconds above threshold
5. If count >= 3: leak confirmed
6. Close valve, create alert, publish MQTT

Server implements identical logic as BACKUP detection.
The inlet ESP32 is the primary safety controller.
The server is the monitoring and backup controller.

Scenario 3 addition:
  After the valve transitions from closed → open (user re-opens after a leak),
  leak detection is suppressed for SETTLE_WINDOW_SECONDS so turbulent flow
  at valve-open time does not immediately re-trigger a false alarm.
  This mirrors the ESP32 isSettling / SETTLE_DURATION_MS logic exactly.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Awaitable

from config import FLOW_MISMATCH_THRESHOLD_LPM, LEAK_CONFIRM_COUNT, HEARTBEAT_TIMEOUT_SEC
from models import ValveState, EventType

logger = logging.getLogger("aquasense.leak")

# Minimum inlet flow that counts as "water is flowing" when valve is closed.
# Anything below this is considered sensor noise and ignored.
VALVE_FAILURE_MIN_FLOW_LPM: float = 0.5

# How long (seconds) to suppress leak detection after the valve is re-opened.
# Matches ESP32 SETTLE_DURATION_MS = 10 000 ms.
SETTLE_WINDOW_SECONDS: int = 10


# ─────────────────────────────────────────────────────────────────────────────
#  Zone runtime state
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ZoneState:
    """
    Runtime state for a single zone's leak detection.
    Tracks the same state variables as the ESP32 inlet device.
    """
    zone_id: int

    inlet_flow_lpm:   float = 0.0
    outlet_flow_lpm:  float = 0.0
    inlet_timestamp:  Optional[datetime] = None
    outlet_timestamp: Optional[datetime] = None

    # Heartbeat tracking — matches ESP32: lastHeartbeatMillis
    last_outlet_heartbeat: Optional[datetime] = None

    # Valve state — kept in sync with Device.valve_state in DB
    valve_state: ValveState = ValveState.UNKNOWN

    # Leak confirmation counter — matches ESP32: leakConfirmCounter
    flow_mismatch_counter: int = 0

    is_leak_active:   bool = False
    leak_detected_at: Optional[datetime] = None

    # Valve failure tracking — flow detected while valve is closed
    is_valve_failure_active:   bool = False
    valve_failure_detected_at: Optional[datetime] = None

    # ── Scenario 3: settle window ─────────────────────────────────────────────
    # Set to a future datetime when the valve transitions closed → open.
    # Leak detection is suppressed until this time passes, matching the
    # ESP32's isSettling / SETTLE_DURATION_MS guard.
    settle_until: Optional[datetime] = None


# ─────────────────────────────────────────────────────────────────────────────
#  Module-level singleton — created by main.py, used by routers
# ─────────────────────────────────────────────────────────────────────────────

_leak_service_instance: Optional["LeakDetectionService"] = None


def get_leak_service() -> Optional["LeakDetectionService"]:
    """Return the module-level instance. Used by routers that need to clear leak state."""
    return _leak_service_instance


def set_leak_service(svc: "LeakDetectionService") -> None:
    global _leak_service_instance
    _leak_service_instance = svc


# ─────────────────────────────────────────────────────────────────────────────
#  LeakDetectionService
# ─────────────────────────────────────────────────────────────────────────────

class LeakDetectionService:
    """
    Server-side leak detection that mirrors ESP32 inlet logic exactly.

    DB writes and MQTT publishes are handled via injected callbacks so this
    class stays pure and testable.
    """

    def __init__(
        self,
        on_leak_detected: Optional[Callable[[int, float, float], Awaitable[None]]] = None,
        on_valve_command: Optional[Callable[[int, str], Awaitable[None]]] = None,
        on_event_created: Optional[Callable[[int, EventType, str, dict], Awaitable[None]]] = None,
    ):
        self._zone_states: Dict[int, ZoneState] = {}
        self._on_leak_detected = on_leak_detected
        self._on_valve_command = on_valve_command
        self._on_event_created = on_event_created

        # MUST MATCH ESP32
        self.threshold_lpm         = FLOW_MISMATCH_THRESHOLD_LPM
        self.confirm_count         = LEAK_CONFIRM_COUNT
        self.heartbeat_timeout_sec = HEARTBEAT_TIMEOUT_SEC

        logger.info(
            "LeakDetectionService ready — threshold=%.1f L/min  confirm=%d  "
            "heartbeat=%.0fs  settle=%ds",
            self.threshold_lpm, self.confirm_count,
            self.heartbeat_timeout_sec, SETTLE_WINDOW_SECONDS,
        )

    def _get_zone_state(self, zone_id: int) -> ZoneState:
        if zone_id not in self._zone_states:
            self._zone_states[zone_id] = ZoneState(zone_id=zone_id)
        return self._zone_states[zone_id]

    # ── Input handlers — called by mqtt_service ───────────────────────────────

    async def update_inlet_flow(self, zone_id: int, flow_lpm: float) -> None:
        """Update inlet flow and run leak evaluation. Called on every inlet reading."""
        state = self._get_zone_state(zone_id)
        state.inlet_flow_lpm  = flow_lpm
        state.inlet_timestamp = datetime.utcnow()
        logger.debug("Zone %d: inlet_flow = %.2f L/min", zone_id, flow_lpm)
        await self._evaluate_leak_condition(zone_id)
        await self._evaluate_valve_failure(zone_id)

    async def update_outlet_flow(self, zone_id: int, flow_lpm: float) -> None:
        """Update outlet flow. Called on every outlet reading."""
        state = self._get_zone_state(zone_id)
        state.outlet_flow_lpm  = flow_lpm
        state.outlet_timestamp = datetime.utcnow()
        logger.debug("Zone %d: outlet_flow = %.2f L/min", zone_id, flow_lpm)

    async def update_outlet_heartbeat(self, zone_id: int) -> None:
        """
        Record outlet device is alive. Called on every heartbeat message.
        Matches ESP32: lastHeartbeatMillis = millis();
        """
        state = self._get_zone_state(zone_id)
        state.last_outlet_heartbeat = datetime.utcnow()
        logger.debug("Zone %d: outlet heartbeat", zone_id)

    async def update_valve_state(self, zone_id: int, valve_state: ValveState) -> None:
        """
        Sync valve state from DB/device. Resets counter on any state change.

        Scenario 3: when the valve transitions from any non-open state → OPEN,
        a 10-second settle window is started. During this window
        _evaluate_leak_condition() returns early without running the mismatch
        check, exactly mirroring the ESP32's isSettling guard.
        """
        state = self._get_zone_state(zone_id)
        if state.valve_state != valve_state:
            logger.info(
                "Zone %d: valve %s → %s",
                zone_id, state.valve_state.value, valve_state.value,
            )
            state.valve_state           = valve_state
            state.flow_mismatch_counter = 0   # reset on every valve change

            if valve_state == ValveState.OPEN:
                # Clear valve-failure flag — flow is now expected
                state.is_valve_failure_active = False

                # ── Start settle window ──────────────────────────────────────
                # Suppress leak detection for SETTLE_WINDOW_SECONDS so the
                # flow rate can stabilise before the mismatch check resumes.
                state.settle_until = datetime.utcnow() + timedelta(seconds=SETTLE_WINDOW_SECONDS)
                logger.info(
                    "Zone %d: valve opened — settle window started (%ds)",
                    zone_id, SETTLE_WINDOW_SECONDS,
                )
            else:
                # Valve closed or unknown — cancel any pending settle window
                state.settle_until = None

    # ── Core detection — MATCHES ESP32 EXACTLY ───────────────────────────────

    async def _evaluate_leak_condition(self, zone_id: int) -> None:
        """
        Mirror of ESP32 checkLeakCondition() with server-side additions.

        Guards (all must pass before the mismatch counter increments):
          STEP 1 — outlet alive?              (matches ESP32: outletAlive check)
          STEP 2 — valve open?                (matches ESP32: valveState == OPEN)
          STEP 2.5 — settle window expired?   (matches ESP32: !isSettling)
          STEP 3 — timestamp alignment?       (server-only: stale delta guard)
          STEP 4 — flow delta > threshold?
          STEP 5 — confirmation counter >= confirm_count?
        """
        state = self._get_zone_state(zone_id)

        # STEP 1 — outlet alive?
        if not self._is_outlet_alive(state):
            if state.flow_mismatch_counter > 0:
                logger.debug("Zone %d: outlet offline — resetting counter", zone_id)
            state.flow_mismatch_counter = 0
            return

        # STEP 2 — valve open?
        if state.valve_state != ValveState.OPEN:
            if state.flow_mismatch_counter > 0:
                logger.debug("Zone %d: valve closed — resetting counter", zone_id)
            state.flow_mismatch_counter = 0
            return

        # STEP 2.5 — settle window (Scenario 3)
        # Mirrors ESP32: if (!isSettling) { ... run leak check ... }
        if state.settle_until is not None:
            now = datetime.utcnow()
            if now < state.settle_until:
                # Still within settle window — discard any accumulated count
                state.flow_mismatch_counter = 0
                remaining = (state.settle_until - now).total_seconds()
                logger.debug(
                    "Zone %d: settle window active — %.1fs remaining, counter reset",
                    zone_id, remaining,
                )
                return
            else:
                # Settle window just expired — clear it and proceed normally
                state.settle_until = None
                logger.info("Zone %d: settle window expired — leak detection resumed", zone_id)

        # STEP 3 — timestamp alignment (server-only stale-delta guard)
        if state.inlet_timestamp and state.outlet_timestamp:
            ts_gap = abs(
                (state.inlet_timestamp - state.outlet_timestamp).total_seconds()
            )
        else:
            ts_gap = 0.0

        if ts_gap > 2.0:
            if state.flow_mismatch_counter > 0:
                logger.debug(
                    "Zone %d: timestamp gap=%.1fs > 2s — resetting counter",
                    zone_id, ts_gap,
                )
            state.flow_mismatch_counter = 0
            return

        # STEP 4 — flow delta
        delta = state.inlet_flow_lpm - state.outlet_flow_lpm

        # STEP 5 — confirmation counter
        if delta > self.threshold_lpm:
            state.flow_mismatch_counter += 1
            logger.debug(
                "Zone %d: delta=%.2f L/min  counter=%d/%d",
                zone_id, delta, state.flow_mismatch_counter, self.confirm_count,
            )
        else:
            if state.flow_mismatch_counter > 0:
                logger.debug("Zone %d: delta normalised — resetting counter", zone_id)
            state.flow_mismatch_counter = 0

        # STEP 6 — confirmed?
        if state.flow_mismatch_counter >= self.confirm_count:
            await self._on_leak_confirmed(zone_id, state)

    def _is_outlet_alive(self, state: ZoneState) -> bool:
        """Matches ESP32: bool outletAlive = (millis() - lastHeartbeatMillis) < HEARTBEAT_TIMEOUT_MS"""
        if state.last_outlet_heartbeat is None:
            return False
        return (datetime.utcnow() - state.last_outlet_heartbeat).total_seconds() < self.heartbeat_timeout_sec

    async def _on_leak_confirmed(self, zone_id: int, state: ZoneState) -> None:
        """
        Matches ESP32 onLeakDetected():
            closeValve(); publishLeakAlert(); leakConfirmCounter = 0;
        """
        if state.is_leak_active:
            return   # already active — don't spam

        state.is_leak_active        = True
        state.leak_detected_at      = datetime.utcnow()
        state.flow_mismatch_counter = 0
        state.settle_until          = None  # cancel any settle window on leak confirm

        delta = state.inlet_flow_lpm - state.outlet_flow_lpm

        logger.warning(
            "LEAK CONFIRMED zone=%d  inlet=%.2f  outlet=%.2f  delta=%.2f L/min",
            zone_id, state.inlet_flow_lpm, state.outlet_flow_lpm, delta,
        )

        if self._on_event_created:
            await self._on_event_created(
                zone_id,
                EventType.LEAK_DETECTED,
                f"Hidden leak: {delta:.2f} L/min lost between inlet and outlet",
                {
                    "inlet_flow_lpm":  state.inlet_flow_lpm,
                    "outlet_flow_lpm": state.outlet_flow_lpm,
                    "delta_lpm":       delta,
                    "threshold_lpm":   self.threshold_lpm,
                    "confirm_count":   self.confirm_count,
                    "source":          "server_backup",
                },
            )

        if self._on_valve_command:
            await self._on_valve_command(zone_id, "close")

        if self._on_leak_detected:
            await self._on_leak_detected(zone_id, state.inlet_flow_lpm, state.outlet_flow_lpm)

    # ── Valve failure detection ───────────────────────────────────────────────

    async def _evaluate_valve_failure(self, zone_id: int) -> None:
        """
        Detect flow through a closed valve.

        Conditions (all must be true):
          • valve_state == CLOSED or UNKNOWN (not OPEN)
          • inlet_flow > VALVE_FAILURE_MIN_FLOW_LPM
          • Not already flagged as active

        This runs on every inlet reading alongside the normal leak check.
        It does NOT close the valve — it only creates a VALVE_FAILURE event.
        """
        state = self._get_zone_state(zone_id)

        # Only check when valve is closed or state unknown
        if state.valve_state == ValveState.OPEN:
            return

        # Ignore sensor noise below minimum threshold
        if state.inlet_flow_lpm <= VALVE_FAILURE_MIN_FLOW_LPM:
            if state.is_valve_failure_active:
                logger.info(
                    "Zone %d: valve failure cleared — flow dropped to %.2f L/min",
                    zone_id, state.inlet_flow_lpm,
                )
                state.is_valve_failure_active = False
            return

        # Flow above threshold while valve is closed
        if state.is_valve_failure_active:
            return   # already flagged — don't spam

        state.is_valve_failure_active   = True
        state.valve_failure_detected_at = datetime.utcnow()

        logger.warning(
            "VALVE FAILURE zone=%d  valve=%s  inlet=%.2f L/min",
            zone_id, state.valve_state.value, state.inlet_flow_lpm,
        )

        if self._on_event_created:
            await self._on_event_created(
                zone_id,
                EventType.VALVE_FAILURE,
                (
                    f"Flow detected with valve {state.valve_state.value}: "
                    f"{state.inlet_flow_lpm:.2f} L/min. "
                    f"Possible causes: valve stuck open, bypass pipe, or upstream leak."
                ),
                {
                    "inlet_flow_lpm": state.inlet_flow_lpm,
                    "valve_state":    state.valve_state.value,
                    "threshold_lpm":  VALVE_FAILURE_MIN_FLOW_LPM,
                },
            )

    async def clear_valve_failure(self, zone_id: int) -> None:
        """Clear valve failure flag for a zone (called when user resolves the alert)."""
        state = self._get_zone_state(zone_id)
        if state.is_valve_failure_active:
            state.is_valve_failure_active = False
            logger.info("Zone %d: valve failure cleared by user", zone_id)

    # ── Manual controls ───────────────────────────────────────────────────────

    async def clear_leak(self, zone_id: int) -> None:
        """
        Clear leak flag when user resolves an alert.
        Valve stays closed — user must open it explicitly via the app toggle.
        A settle window is NOT started here — it starts when the valve is
        actually opened (update_valve_state called with OPEN).
        """
        state = self._get_zone_state(zone_id)
        if not state.is_leak_active:
            return

        duration                    = self._get_leak_duration(state)
        state.is_leak_active        = False
        state.flow_mismatch_counter = 0

        logger.info("Zone %d: leak cleared by user (duration=%.0fs)", zone_id, duration or 0)

        if self._on_event_created:
            await self._on_event_created(
                zone_id,
                EventType.LEAK_CLEARED,
                "Leak alert cleared by user",
                {"cleared_by": "user", "leak_duration_sec": duration},
            )

    def _get_leak_duration(self, state: ZoneState) -> Optional[float]:
        if state.leak_detected_at:
            return (datetime.utcnow() - state.leak_detected_at).total_seconds()
        return None

    # ── Status queries ────────────────────────────────────────────────────────

    def get_zone_state(self, zone_id: int) -> Optional[ZoneState]:
        return self._zone_states.get(zone_id)

    def get_all_zone_states(self) -> Dict[int, ZoneState]:
        return self._zone_states.copy()

    def is_leak_active(self, zone_id: int) -> bool:
        state = self._zone_states.get(zone_id)
        return state.is_leak_active if state else False

    def is_settling(self, zone_id: int) -> bool:
        """Returns True if this zone is currently in the post-open settle window."""
        state = self._zone_states.get(zone_id)
        if state and state.settle_until:
            return datetime.utcnow() < state.settle_until
        return False

    def get_current_delta(self, zone_id: int) -> Optional[float]:
        state = self._zone_states.get(zone_id)
        if state and state.inlet_timestamp and state.outlet_timestamp:
            return state.inlet_flow_lpm - state.outlet_flow_lpm
        return None