# api/routes/webhooks.py
"""
Webhook endpoints for receiving events from external services.

This module handles incoming webhooks from:
- ai-video-backend: User lifecycle events (signup, login)
"""
import hashlib
import hmac
import logging
import os
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, EmailStr

from config.settings import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Configuration
WEBHOOK_SECRET = os.getenv("AUTH_WEBHOOK_SECRET", "")
ADMIN_TELEGRAM_CHAT_ID = os.getenv("ADMIN_TELEGRAM_CHAT_ID", "2055631678")


# ──────────────────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────────────────

class WebhookUser(BaseModel):
    """User data from webhook payload."""
    id: int
    email: EmailStr
    username: Optional[str] = None
    date_joined: Optional[str] = None
    provider: str = "email"


class AuthWebhookPayload(BaseModel):
    """Payload from ai-video-backend user webhooks."""
    event: str
    timestamp: str
    user: WebhookUser
    data: Optional[dict] = None


class WebhookResponse(BaseModel):
    """Standard webhook response."""
    status: str
    message: str


# ──────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────

def verify_signature(payload: bytes, signature: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.
    
    Args:
        payload: Raw request body bytes
        signature: Signature from X-Webhook-Signature header
        
    Returns:
        True if signature is valid or no secret configured
    """
    if not WEBHOOK_SECRET:
        logger.warning("No WEBHOOK_SECRET configured - skipping signature verification")
        return True
    
    if not signature:
        logger.warning("Missing signature header")
        return False
    
    expected = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


async def send_telegram_alert(message: str, chat_id: str = None) -> bool:
    """
    Send a Telegram alert to admin.
    
    Args:
        message: Message text (supports Markdown)
        chat_id: Target chat ID (defaults to ADMIN_TELEGRAM_CHAT_ID)
        
    Returns:
        True if sent successfully
    """
    bot_token = Config.TELEGRAM_BOT_TOKEN
    target_chat = chat_id or ADMIN_TELEGRAM_CHAT_ID
    
    if not bot_token or not target_chat:
        logger.warning("Telegram bot token or chat ID not configured")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json={
                "chat_id": target_chat,
                "text": message,
                "parse_mode": "Markdown"
            })
            
            if response.status_code == 200:
                logger.info(f"Telegram alert sent to {target_chat}")
                return True
            else:
                logger.warning(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False


async def ensure_user_in_airtable(user: WebhookUser) -> dict:
    """
    Ensure user exists in Airtable user_configs table.
    Creates a new record if user doesn't exist.
    
    Args:
        user: User data from webhook
        
    Returns:
        Airtable record dict
    """
    from pyairtable import Api
    from pyairtable.formulas import EQ, Field
    
    try:
        api = Api(Config.AIRTABLE_API_KEY)
        table = api.table(Config.AIRTABLE_BASE_ID, Config.AIRTABLE_TABLE_ID_USER_CONFIGS)
        
        # Check if user already exists
        formula = str(EQ(Field("user_email"), user.email))
        existing = table.all(formula=formula, max_records=1)
        
        if existing:
            logger.info(f"User {user.email} already exists in Airtable")
            # Update last seen
            record_id = existing[0]['id']
            table.update(record_id, {
                "last_active_at": datetime.utcnow().isoformat(),
                # auth_user_id removed - field doesn"t exist in Airtable
            })
            return existing[0]
        
        # Create new user record
        new_record = table.create({
            "user_email": user.email,
            # "auth_user_id": user.id,  # Field doesn"t exist
            "plan": "free",
            "signup_provider": user.provider,
            "created_at": user.date_joined or datetime.utcnow().isoformat(),
            "last_active_at": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"Created Airtable record for new user: {user.email}")
        return new_record
        
    except Exception as e:
        logger.error(f"Airtable error for user {user.email}: {e}")
        raise


# ──────────────────────────────────────────────────────────
# Webhook Endpoints
# ──────────────────────────────────────────────────────────

@router.post("/auth", response_model=WebhookResponse)
async def handle_auth_webhook(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature")
):
    """
    Handle user lifecycle webhooks from ai-video-backend.
    
    Events:
    - user.created: New user signup
    - user.login: User logged in
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature
    if not verify_signature(body, x_webhook_signature or ""):
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    try:
        payload = AuthWebhookPayload.model_validate_json(body)
    except Exception as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    
    logger.info(f"Received auth webhook: {payload.event} for {payload.user.email}")
    
    # Handle events
    if payload.event == "user.created":
        await handle_user_created(payload)
    elif payload.event == "user.login":
        await handle_user_login(payload)
    else:
        logger.warning(f"Unknown event type: {payload.event}")
    
    return WebhookResponse(status="ok", message=f"Processed {payload.event}")


async def handle_user_created(payload: AuthWebhookPayload):
    """
    Handle new user signup.
    
    1. Create/update Airtable record
    2. Send Telegram alert to admin
    """
    user = payload.user
    
    # Ensure user exists in Airtable
    try:
        await ensure_user_in_airtable(user)
    except Exception as e:
        logger.error(f"Failed to create Airtable record: {e}")
        # Don't fail the webhook - alert will still send
    
    # Send Telegram alert
    timestamp = datetime.fromisoformat(payload.timestamp.replace('Z', '+00:00'))
    local_time = timestamp.strftime('%Y-%m-%d %H:%M UTC')
    
    message = (
        "🎉 *New WinningCV Signup!*\n\n"
        f"📧 *Email:* `{user.email}`\n"
        f"🔐 *Provider:* {user.provider.title()}\n"
        f"🕐 *Time:* {local_time}\n"
        f"🆔 *User ID:* {user.id}"
    )
    
    await send_telegram_alert(message)


async def handle_user_login(payload: AuthWebhookPayload):
    """
    Handle user login event.
    
    Updates last_active_at in Airtable (lightweight, no alert).
    """
    user = payload.user
    
    try:
        await ensure_user_in_airtable(user)
    except Exception as e:
        logger.debug(f"Could not update user on login: {e}")


@router.get("/auth/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "healthy",
        "endpoint": "/api/v1/webhooks/auth",
        "signature_required": bool(WEBHOOK_SECRET)
    }
