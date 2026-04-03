# usage_router.py
# AquaSense — Usage summary endpoint
#   GET /usage/summary  → summary of water usage for a given month (defaults to current month)
# Reads from daily_summaries (pre-aggregated by aggregation.py).
# Scoped to the user's network via owner_id — consistent with all other routers.
#
# Fix vs original version:
#   • Removed `summary_date < DATE_TRUNC('month', CURRENT_DATE)` which was
#     incorrectly excluding the current month's data.
#   • Ownership scoped through Network.owner_id (not user_id on readings).
#   • Uses ORM instead of raw text() SQL.
#   • weekly_avg = daily_avg * 7 (correct formula).
#   • projected_monthly_total added — for in-progress months this extrapolates
#     the daily average across the full month so the displayed number is not
#     misleadingly low just because the month isn't finished yet.

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
    monthly_total:           float   # actual litres recorded so far this month
    projected_monthly_total: float   # extrapolated to full month (= monthly_total for past months)
    is_projected:            bool    # True when viewing the current in-progress month
    weekly_avg:              float
    daily_avg:               float
    leak_count:              int
    year:                    int
    month:                   int
    days_in_month:           int     # total days in the selected month
    days_with_data:          int     # days that have aggregated readings


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    year:       int           = Query(default=datetime.now(timezone.utc).year),
    month:      int           = Query(default=datetime.now(timezone.utc).month, ge=1, le=12),
    network_id: Optional[int] = Query(default=None),
    db:         AsyncSession  = Depends(get_db),
    current_user: User        = Depends(get_current_user),
):
    # Resolve network — consistent with all other routers
    net_query = select(Network).where(Network.owner_id == current_user.id)
    if network_id:
        net_query = net_query.where(Network.id == network_id)
    net_result = await db.execute(net_query.limit(1))
    network = net_result.scalar_one_or_none()
    if not network:
        raise HTTPException(status_code=404, detail="No network found")

    # Active outlet device IDs for this network
    dev_result = await db.execute(
        select(Device.device_id).where(
            Device.network_id  == network.id,
            Device.sensor_type == "outlet",
            Device.status      == "active",
        )
    )
    device_ids = [row[0] for row in dev_result.all()]

    today         = date.today()
    days_in_month = monthrange(year, month)[1]

    # Is the user viewing the current in-progress month?
    is_current_month = (year == today.year and month == today.month)

    # For projection: how many days have elapsed so far (including today).
    # For past months this equals days_in_month, so projection == actual.
    days_elapsed = today.day if is_current_month else days_in_month

    _empty = UsageSummary(
        monthly_total           = 0.0,
        projected_monthly_total = 0.0,
        is_projected            = is_current_month,
        weekly_avg              = 0.0,
        daily_avg               = 0.0,
        leak_count              = 0,
        year                    = year,
        month                   = month,
        days_in_month           = days_in_month,
        days_with_data          = 0,
    )

    if not device_ids:
        return _empty

    # Aggregate from daily_summaries for the requested year/month.
    # No date ceiling — we want ALL rows for the month including today.
    result = await db.execute(
        select(
            func.sum(DailySummary.total_volume_litres).label("monthly_total"),
            func.sum(DailySummary.leak_event_count).label("leak_count"),
            func.count(DailySummary.id).label("days_with_data"),
        )
        .where(
            DailySummary.device_id.in_(device_ids),
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

    # daily_avg: average over days that actually had readings
    daily_avg = monthly_total / days_with_data if days_with_data else 0.0

    # projected_monthly_total:
    #   Past month    → same as monthly_total (month is complete, no projection needed)
    #   Current month → daily_avg × days_in_month
    #     e.g. 10 days elapsed, 15,000 L recorded → daily_avg = 1,500 L/day
    #          projected = 1,500 × 31 = 46,500 L
    #   This gives the user a realistic estimate of what the full month will cost,
    #   rather than showing a misleadingly low mid-month number.
    if is_current_month and days_with_data > 0:
        projected_monthly_total = daily_avg * days_in_month
    else:
        projected_monthly_total = monthly_total   # past month — no extrapolation

    weekly_avg = daily_avg * 7

    return UsageSummary(
        monthly_total           = round(monthly_total,           1),
        projected_monthly_total = round(projected_monthly_total, 1),
        is_projected            = is_current_month,
        weekly_avg              = round(weekly_avg, 1),
        daily_avg               = round(daily_avg,  1),
        leak_count              = leak_count,
        year                    = year,
        month                   = month,
        days_in_month           = days_in_month,
        days_with_data          = days_with_data,
    )