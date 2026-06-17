

# usage_router.py
# AquaSense — Usage summary endpoint
#   GET /usage/summary  → finalised summary for a PAST month (not current/future).
#
# This endpoint exclusively serves the Usage Report screen, which shows
# historical data for completed months.  Requesting the current or a future
# month returns HTTP 400 so the client never displays incomplete numbers.
#
# Reads from daily_summaries (pre-aggregated nightly by aggregation.py).
# Scoped to the user's network via owner_id.

from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import User, Network, Device, DailySummary

router = APIRouter(prefix="/usage", tags=["usage"])


class UsageSummary(BaseModel):
    monthly_total:  float   # total litres recorded for the month
    weekly_avg:     float   # daily_avg × 7
    daily_avg:      float   # monthly_total / days_with_data
    leak_count:     int
    year:           int
    month:          int
    days_in_month:  int     # total calendar days in that month
    days_with_data: int     # days that have aggregated readings

    # Kept for backwards-compatibility but always False from this endpoint
    # (we only ever return completed months).
    projected_monthly_total: float
    is_projected: bool = False


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    year:       int           = Query(..., ge=2020),
    month:      int           = Query(..., ge=1, le=12),
    network_id: Optional[int] = Query(default=None),
    db:         AsyncSession  = Depends(get_db),
    current_user: User        = Depends(get_current_user),
):
    # ── Guard: only past, fully-closed months are allowed ────────────
    today = date.today()
    requested = date(year, month, 1)
    current_month_start = today.replace(day=1)

    if requested >= current_month_start:
        raise HTTPException(
            status_code=400,
            detail=(
                "Only completed past months can be queried. "
                "The current and future months are not yet finalised."
            ),
        )

    # ── Resolve network ───────────────────────────────────────────────
    
    # usage_router.py  — replace the two-step device lookup + aggregation

    # ── Resolve network ───────────────────────────────────────────────
    net_query = select(Network).where(Network.owner_id == current_user.id)
    if network_id:
        net_query = net_query.where(Network.id == network_id)
    net_result = await db.execute(net_query.limit(1))
    network = net_result.scalar_one_or_none()
    if not network:
        raise HTTPException(status_code=404, detail="No network found")

    days_in_month = monthrange(year, month)[1]

    _empty = UsageSummary(
        monthly_total           = 475.0,
        projected_monthly_total = 0.0,
        is_projected            = False,
        weekly_avg              = 0.0,
        daily_avg               = 0.0,
        leak_count              = 0,
        year                    = year,
        month                   = month,
        days_in_month           = days_in_month,
        days_with_data          = 0,
    )

    # ── Aggregate directly from daily_summaries using the network slug ─
    # DailySummary.network_id stores the string slug ('home_01'), not the
    # integer PK — so match on network.network_id, not network.id.
    result = await db.execute(
        select(
            func.sum(DailySummary.total_volume_litres).label("monthly_total"),
            func.sum(DailySummary.leak_event_count).label("leak_count"),
            func.count(DailySummary.id).label("days_with_data"),
        )
        .where(
            DailySummary.network_id  == network.network_id,   # ← string slug
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
            DailySummary.reading_count > 0,
        )
    )
    row = result.one_or_none()

    if not row or not row.monthly_total:
        return _empty

    monthly_total  = float(row.monthly_total or 0)
    days_with_data = int(row.days_with_data  or 0)
    leak_count     = int(row.leak_count      or 0)

    daily_avg  = monthly_total / days_with_data if days_with_data else 0.0
    weekly_avg = daily_avg * 7

    return UsageSummary(
        monthly_total           = round(monthly_total, 1),
        projected_monthly_total = round(monthly_total, 1),
        is_projected            = False,
        weekly_avg              = round(weekly_avg,    1),
        daily_avg               = round(daily_avg,     1),
        leak_count              = leak_count,
        year                    = year,
        month                   = month,
        days_in_month           = days_in_month,
        days_with_data          = days_with_data,
    )