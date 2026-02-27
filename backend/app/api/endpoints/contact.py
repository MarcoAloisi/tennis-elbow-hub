"""Contact form endpoint — receives messages and sends them via email."""

import logging
import smtplib
from email.mime.text import MIMEText

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contact", tags=["contact"])


class ContactRequest(BaseModel):
    """Validated contact form payload."""

    name: str = Field(..., min_length=1, max_length=100)
    discord: str = Field(..., min_length=2, max_length=100)
    message: str = Field(..., min_length=10, max_length=2000)


@router.post("/send")
@limiter.limit("3/minute")
async def send_contact_message(request: Request, payload: ContactRequest) -> dict[str, str]:
    """Receive a contact form submission and forward it via email."""
    settings = get_settings()
    recipient = settings.contact_email

    subject = f"[Tennis Elbow Hub] Message from {payload.name}"
    body = (
        f"Name: {payload.name}\n"
        f"Discord: {payload.discord}\n"
        f"---\n\n"
        f"{payload.message}"
    )

    # Build the email
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = recipient

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("Contact email sent from %s (%s)", payload.name, payload.discord)
        return {"status": "ok"}
    except Exception:
        logger.exception("Failed to send contact email")
        raise HTTPException(
            status_code=500,
            detail="Failed to send message. Please try again later.",
        )
