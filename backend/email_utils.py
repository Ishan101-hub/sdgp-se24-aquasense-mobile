# email_utils.py
# AquaSense — Email utilities (Kulith's implementation)
# Reads credentials from config.settings instead of app.config.

import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import settings


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


async def send_email(to_email: str, otp: str, email_type: str):
    subject_map = {
        "verification": "AquaSense — Verify Your Email",
        "reset":        "AquaSense — Password Reset OTP",
        "2fa":          "AquaSense — Your 2FA Code",
    }
    body_map = {
        "verification": f"""
        <h2>Welcome to AquaSense</h2>
        <p>Your email verification code is:</p>
        <h1 style="color: #1A1A6E;">{otp}</h1>
        <p>This code expires in 10 minutes.</p>
        <p>If you did not create an account, please ignore this email.</p>
        """,
        "reset": f"""
        <h2>AquaSense Password Reset</h2>
        <p>Your password reset code is:</p>
        <h1 style="color: #1A1A6E;">{otp}</h1>
        <p>This code expires in 10 minutes.</p>
        <p>If you did not request this, please ignore this email.</p>
        """,
        "2fa": f"""
        <h2>AquaSense Two-Factor Authentication</h2>
        <p>Your 2FA verification code is:</p>
        <h1 style="color: #1A1A6E;">{otp}</h1>
        <p>This code expires in 10 minutes.</p>
        <p>If you did not request this, please secure your account immediately.</p>
        """,
    }

    subject = subject_map.get(email_type, "AquaSense Notification")
    body    = body_map.get(email_type, otp)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.EMAIL_USER
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
        server.sendmail(settings.EMAIL_USER, to_email, msg.as_string())


async def send_login_alert_email(to_email: str, name: str, device_info: str, time: str):
    subject = "AquaSense — New Login Detected"
    body    = f"""
    <h2>New Login to Your AquaSense Account</h2>
    <p>Hello {name},</p>
    <p>A new login was detected on your account.</p>
    <table>
        <tr><td><b>Time:</b></td><td>{time}</td></tr>
        <tr><td><b>Device:</b></td><td>{device_info}</td></tr>
    </table>
    <p>If this was you, no action is needed.</p>
    <p>If this was not you, please change your password immediately.</p>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.EMAIL_USER
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
        server.sendmail(settings.EMAIL_USER, to_email, msg.as_string())
