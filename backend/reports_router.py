# reports_router.py
# AquaSense — Monthly report PDF endpoint
#   GET /reports/monthly?year=2026&month=3
#
# Pulls the same data as /usage/summary (daily_summaries via network slug),
# builds a clean PDF with reportlab, and streams it back as application/pdf.
# The Flutter client saves the bytes to disk and opens them with open_filex.

import io
from calendar import monthrange
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from auth import get_current_user
from database import get_db
from models import User, Network, DailySummary

router = APIRouter(prefix="/reports", tags=["reports"])

# ── Colour palette (matches the AquaSense app) ────────────────
AQUA   = colors.HexColor("#04775B")   # aquaAccent
NAVY   = colors.HexColor("#0A1B6F")   # mainTextColor
LIGHT  = colors.HexColor("#F0FAF7")   # light aqua tint
RED    = colors.HexColor("#FF5252")   # leak / alert colour
GREY   = colors.HexColor("#9E9E9E")

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _fmt(val: float) -> str:
    """Format a float with thousands separator and one decimal place."""
    return f"{val:,.1f}"


def _card_cell(label: str, value: str, value_colour) -> Paragraph:
    """
    Returns a single Paragraph with the label on the first line and the
    value on the second — using reportlab's inline XML tags so no nested
    Table is needed. Flat Paragraphs always render reliably in table cells.
    """
    hex_colour = value_colour.hexval() if hasattr(value_colour, "hexval") else "#000000"
    html = (
        f'<font size="8" color="#9E9E9E">{label}</font><br/>'
        f'<font size="18" color="{hex_colour}"><b>{value}</b></font>'
    )
    return Paragraph(html, ParagraphStyle(
        f"card_{label}",
        alignment=TA_CENTER,
        leading=26,
        spaceAfter=0,
    ))


def _build_pdf(
    user_name:      str,
    year:           int,
    month:          int,
    monthly_total:  float,
    daily_avg:      float,
    weekly_avg:     float,
    leak_count:     int,
    days_with_data: int,
    days_in_month:  int,
    daily_rows:     list[dict],
) -> bytes:
    """Build the PDF in memory and return raw bytes."""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    W           = A4[0] - 40 * mm
    styles      = getSampleStyleSheet()
    month_label = f"{MONTH_NAMES[month - 1]} {year}"

    # ── Paragraph styles ──────────────────────────────────────
    title_style = ParagraphStyle(
        "AqTitle", parent=styles["Normal"],
        fontSize=22, textColor=NAVY, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "AqSub", parent=styles["Normal"],
        fontSize=10, textColor=GREY, alignment=TA_CENTER, spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "AqSection", parent=styles["Normal"],
        fontSize=12, textColor=AQUA, fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=4,
    )
    footer_style = ParagraphStyle(
        "AqFooter", parent=styles["Normal"],
        fontSize=8, textColor=GREY, alignment=TA_CENTER,
    )

    story = []

    # ── Header ────────────────────────────────────────────────
    story.append(Paragraph("AquaSense", title_style))
    story.append(Paragraph("Smart Water Monitoring System", sub_style))
    story.append(Paragraph(f"Monthly Usage Report — {month_label}", sub_style))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=2, color=AQUA, spaceAfter=6))

    # ── Report meta ───────────────────────────────────────────
    meta_data = [
        ["Account",        user_name],
        ["Report for",     month_label],
        ["Generated",      date.today().strftime("%d %B %Y")],
        ["Data coverage",  f"{days_with_data} of {days_in_month} days"],
    ]
    meta_table = Table(meta_data, colWidths=[40 * mm, W - 40 * mm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 0), (0, -1),  NAVY),
        ("TEXTCOLOR",     (1, 0), (1, -1),  colors.black),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # ── Summary cards (2 × 2 grid, flat Paragraphs only) ─────
    story.append(Paragraph("Usage Summary", section_style))

    half = W / 2 - 3 * mm
    card_data = [
        [
            _card_cell("Total Monthly Usage", f"{_fmt(monthly_total)} L", AQUA),
            _card_cell("Daily Average",        f"{_fmt(daily_avg)} L",    NAVY),
        ],
        [
            _card_cell("Weekly Average",       f"{_fmt(weekly_avg)} L",   NAVY),
            _card_cell("Leaks Detected",       str(leak_count),            RED),
        ],
    ]
    card_table = Table(
        card_data,
        colWidths=[half, half],
        rowHeights=[28 * mm, 28 * mm],
    )
    card_table.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND",    (0, 0), (0, 0),   LIGHT),
        ("BACKGROUND",    (1, 0), (1, 0),   colors.HexColor("#F0F2FF")),
        ("BACKGROUND",    (0, 1), (0, 1),   colors.HexColor("#F0F2FF")),
        ("BACKGROUND",    (1, 1), (1, 1),   colors.HexColor("#FFF5F5")),
        ("BOX",           (0, 0), (0, 0),   0.5, AQUA),
        ("BOX",           (1, 0), (1, 0),   0.5, NAVY),
        ("BOX",           (0, 1), (0, 1),   0.5, NAVY),
        ("BOX",           (1, 1), (1, 1),   0.5, RED),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 6 * mm))

    # ── Daily breakdown table ─────────────────────────────────
    if daily_rows:
        story.append(Paragraph("Daily Breakdown", section_style))

        rows = [["Date", "Volume (L)", "Leaks"]]
        for r in daily_rows:
            rows.append([
                r["date"],
                _fmt(r["volume"]),
                str(r["leaks"]) if r["leaks"] else "-",
            ])

        # Build leak-row colour directives before constructing the style list
        leak_directives = [
            ("TEXTCOLOR", (2, i + 1), (2, i + 1), RED)
            for i, r in enumerate(daily_rows) if r["leaks"]
        ]

        col_w = [65 * mm, W - 105 * mm, 40 * mm]
        tbl   = Table(rows, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  AQUA),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN",         (0, 0), (0, -1),  "LEFT"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FDFB")]),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#E0E0E0")),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            *leak_directives,
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6 * mm))

    # ── Footer ────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY, spaceBefore=6))
    story.append(Paragraph(
        f"This report was automatically generated by AquaSense on "
        f"{date.today().strftime('%d %B %Y')}. "
        "Data is sourced from finalised daily summaries only.",
        footer_style,
    ))

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════
#  Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/monthly")
async def get_monthly_report(
    year:       int           = Query(..., ge=2020),
    month:      int           = Query(..., ge=1, le=12),
    network_id: Optional[int] = Query(default=None),
    db:         AsyncSession  = Depends(get_db),
    current_user: User        = Depends(get_current_user),
):
    # ── Guard: past months only ───────────────────────────────
    today = date.today()
    if date(year, month, 1) >= today.replace(day=1):
        raise HTTPException(
            status_code=400,
            detail="Reports can only be generated for completed past months.",
        )

    # ── Resolve network ───────────────────────────────────────
    net_query = select(Network).where(Network.owner_id == current_user.id)
    if network_id:
        net_query = net_query.where(Network.id == network_id)
    net_result = await db.execute(net_query.limit(1))
    network = net_result.scalar_one_or_none()
    if not network:
        raise HTTPException(status_code=404, detail="No network found for this user.")

    # ── Aggregate totals ──────────────────────────────────────
    agg = await db.execute(
        select(
            func.sum(DailySummary.total_volume_litres).label("monthly_total"),
            func.sum(DailySummary.leak_event_count).label("leak_count"),
            func.count(DailySummary.id).label("days_with_data"),
        ).where(
            DailySummary.network_id  == network.network_id,
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
            DailySummary.reading_count > 0,
        )
    )
    row = agg.one_or_none()

    monthly_total  = float(row.monthly_total  or 0) if row else 0.0
    leak_count     = int(row.leak_count       or 0) if row else 0
    days_with_data = int(row.days_with_data   or 0) if row else 0
    days_in_month  = monthrange(year, month)[1]

    daily_avg  = monthly_total / days_with_data if days_with_data else 0.0
    weekly_avg = daily_avg * 7

    # ── Per-day rows for the breakdown table ──────────────────
    daily_result = await db.execute(
        select(
            DailySummary.summary_date,
            func.sum(DailySummary.total_volume_litres).label("volume"),
            func.sum(DailySummary.leak_event_count).label("leaks"),
        ).where(
            DailySummary.network_id  == network.network_id,
            DailySummary.sensor_type == "outlet",
            extract("year",  DailySummary.summary_date) == year,
            extract("month", DailySummary.summary_date) == month,
            DailySummary.reading_count > 0,
        ).group_by(DailySummary.summary_date)
         .order_by(DailySummary.summary_date)
    )
    daily_rows = [
        {
            "date":   r.summary_date.strftime("%d %b %Y"),
            "volume": float(r.volume or 0),
            "leaks":  int(r.leaks or 0),
        }
        for r in daily_result.all()
    ]

    # ── Build PDF ─────────────────────────────────────────────
    pdf_bytes = _build_pdf(
        user_name      = current_user.name or current_user.email,
        year           = year,
        month          = month,
        monthly_total  = monthly_total,
        daily_avg      = daily_avg,
        weekly_avg     = weekly_avg,
        leak_count     = leak_count,
        days_with_data = days_with_data,
        days_in_month  = days_in_month,
        daily_rows     = daily_rows,
    )

    filename = f"aquasense_report_{year}_{str(month).zfill(2)}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )