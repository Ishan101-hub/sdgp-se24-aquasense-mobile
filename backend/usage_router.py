from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from database import get_db
from auth import get_current_user

router = APIRouter(prefix="/usage", tags=["usage"])


class UsageSummary(BaseModel):
    monthly_total: float
    weekly_avg: float
    daily_avg: float
    leak_count: int
    year: int
    month: int


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(text("""
SELECT
    COALESCE(SUM(ds.total_volume_litres), 0) AS monthly_total,
    COALESCE(AVG(ds.total_volume_litres), 0) * 7 AS weekly_avg,
    COALESCE(AVG(ds.total_volume_litres), 0) AS daily_avg,
    COALESCE(SUM(ds.leak_event_count), 0) AS leak_count
FROM daily_summaries ds
JOIN devices d ON ds.device_id = d.device_id
JOIN networks n ON d.network_id = n.id
WHERE n.owner_id = :user_id
  AND ds.summary_date >= DATE_TRUNC('month', MAKE_DATE(:year, :month, 1))
  AND ds.summary_date < DATE_TRUNC('month', MAKE_DATE(:year, :month, 1)) + INTERVAL '1 month'
  AND ds.summary_date < DATE_TRUNC('month', CURRENT_DATE);
"""), {
    "user_id": current_user.id,
    "year": year,
    "month": month
})

    row = result.fetchone()

    return UsageSummary(
        monthly_total=round(float(row.monthly_total), 1),
        weekly_avg=round(float(row.weekly_avg), 1),
        daily_avg=round(float(row.daily_avg), 1),
        leak_count=int(row.leak_count),
        year=year,
        month=month,
    )