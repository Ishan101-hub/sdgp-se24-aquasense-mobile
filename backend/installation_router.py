# installation_router.py
# AquaSense — Installation request routes with Resend Alerts

from datetime import date
import resend

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import InstallationRequest, User

from config import settings
resend.api_key = settings.RESEND_API_KEY

router = APIRouter(prefix="/installation", tags=["Installation"])

class InstallationRequestSchema(BaseModel):
    address:        str
    num_zones:      int
    preferred_date: date

    @field_validator("address")
    @classmethod
    def validate_address(cls, v):
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Address must be at least 5 characters")
        if len(v) > 300:
            raise ValueError("Address must not exceed 300 characters")
        return v

    @field_validator("num_zones")
    @classmethod
    def validate_zones(cls, v):
        if v < 1:
            raise ValueError("Must have at least 1 zone")
        if v > 50:
            raise ValueError("Cannot exceed 50 zones")
        return v

    @field_validator("preferred_date")
    @classmethod
    def validate_date(cls, v):
        if v < date.today():
            raise ValueError("Preferred date cannot be in the past")
        return v


# ── Helper function to send the email alert ─────────────────
def send_admin_email_alert(user_email: str, address: str, num_zones: int, preferred_date: str):
    """
    Compiles an HTML template and shoots it off to the admin inbox.
    """
    html_content = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
        <h2 style="color: #0A1B6F; border-bottom: 2px solid #0A1B6F; padding-bottom: 8px;">🚨 New Installation Request</h2>
        <p>A user has submitted a new hardware installation request via the AquaSense app.</p>
        
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr>
                <td style="padding: 8px; font-weight: bold; background: #f9f9f9; width: 35%;">Customer Email:</td>
                <td style="padding: 8px; background: #f9f9f9;">{user_email}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Property Address:</td>
                <td style="padding: 8px;">{address}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold; background: #f9f9f9;">Number of Zones:</td>
                <td style="padding: 8px; background: #f9f9f9;"><span style="background: #0A1B6F; color: white; padding: 2px 8px; border-radius: 4px; font-size: 13px;">{num_zones} Zones</span></td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Preferred Date:</td>
                <td style="padding: 8px; color: #d93838; font-weight: 500;">{preferred_date}</td>
            </tr>
        </table>
        
        <div style="margin-top: 25px; font-size: 12px; color: #777; text-align: center; border-top: 1px solid #eee; padding-top: 12px;">
            AquaSense Core Backend Automation Engine • Resend Delivery Integration
        </div>
    </div>
    """

    try:
        resend.Emails.send({
            # NOTE: If your Resend domain isn't verified yet, you must use 'onboarding@resend.dev' as the sender.
            "from": "AquaSense Alerts <onboarding@resend.dev>",
            "to": ["aquasenze@gmail.com"],
            "subject": f"🚨 New Installation Request - {num_zones} Zones",
            "html": html_content
        })
    except Exception as e:
        # Log the error but don't crash the API response for the user
        print(f"[RESEND ERROR] Failed to send admin alert email: {e}")


@router.post("")
async def request_installation(
    data:             InstallationRequestSchema,
    background_tasks: BackgroundTasks, # FastAPI utility to run jobs without making the user wait
    current_user:     User = Depends(get_current_user),
    db:               AsyncSession = Depends(get_db),
):
    # 1. Save to database
    req = InstallationRequest(
        user_id        = current_user.id,
        address        = data.address,
        num_zones      = data.num_zones,
        preferred_date = data.preferred_date,
    )
    db.add(req)
    await db.commit()
    
    # 2. Push the email delivery off into a background thread
    # This prevents the mobile app from lagging while waiting for the network call to Resend
    background_tasks.add_task(
        send_admin_email_alert,
        user_email     = current_user.email,
        address        = data.address,
        num_zones      = data.num_zones,
        preferred_date = str(data.preferred_date)
    )
    
    return {"message": "Installation request submitted successfully"}