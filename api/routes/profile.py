"""
Profile and notification preferences routes for WinningCV API.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from api.schemas.auth import UserInfo
from api.schemas.notifications import (
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationPreferencesResponse,
    TestNotificationRequest,
    TestNotificationResponse
)
from api.middleware.auth_middleware import get_current_user
from data_store.airtable_manager import AirtableManager
from config.settings import Config
from utils.notifications import (
    send_email_notification,
    send_telegram_to_user,
    send_wechat_message
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Profile"])


def get_airtable_manager() -> AirtableManager:
    """Get Airtable manager instance"""
    return AirtableManager(
        api_key=Config.AIRTABLE_API_KEY,
        base_id=Config.AIRTABLE_BASE_ID,
        table_id=Config.AIRTABLE_TABLE_ID
    )


@router.get("/notifications", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    user: UserInfo = Depends(get_current_user)
) -> NotificationPreferencesResponse:
    """
    Get current user's notification preferences.
    Returns default preferences if none are set.
    """
    try:
        manager = get_airtable_manager()
        prefs = manager.get_notification_preferences(user.email)

        wechat_id = prefs.get("wechat_id") or prefs.get("wechat_openid")
        return NotificationPreferencesResponse(
            user_email=user.email,
            email_alerts=prefs.get("email_alerts", True),
            telegram_alerts=prefs.get("telegram_alerts", False),
            wechat_alerts=prefs.get("wechat_alerts", False),
            weekly_digest=prefs.get("weekly_digest", True),
            telegram_chat_id=prefs.get("telegram_chat_id"),
            wechat_id=wechat_id,
            wechat_openid=wechat_id,  # For backward compatibility
            notification_email=prefs.get("notification_email") or user.email
        )
    except Exception as e:
        logger.error(f"Failed to get notification preferences: {e}")
        # Return defaults on error
        return NotificationPreferencesResponse(
            user_email=user.email,
            email_alerts=True,
            telegram_alerts=False,
            wechat_alerts=False,
            weekly_digest=True,
            notification_email=user.email
        )


@router.put("/notifications", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    user: UserInfo = Depends(get_current_user)
) -> NotificationPreferencesResponse:
    """
    Update current user's notification preferences.
    Only updates fields that are provided (non-null).
    """
    try:
        manager = get_airtable_manager()

        # Get existing preferences
        existing = manager.get_notification_preferences(user.email)

        # Build update dict with only provided fields
        # Support both wechat_id and wechat_openid for backward compatibility
        new_wechat_id = preferences.wechat_id or preferences.wechat_openid
        existing_wechat_id = existing.get("wechat_id") or existing.get("wechat_openid")
        wechat_id = new_wechat_id if new_wechat_id is not None else existing_wechat_id

        update_data = {
            "user_email": user.email,
            "email_alerts": preferences.email_alerts if preferences.email_alerts is not None else existing.get("email_alerts", True),
            "telegram_alerts": preferences.telegram_alerts if preferences.telegram_alerts is not None else existing.get("telegram_alerts", False),
            "wechat_alerts": preferences.wechat_alerts if preferences.wechat_alerts is not None else existing.get("wechat_alerts", False),
            "weekly_digest": preferences.weekly_digest if preferences.weekly_digest is not None else existing.get("weekly_digest", True),
            "telegram_chat_id": preferences.telegram_chat_id if preferences.telegram_chat_id is not None else existing.get("telegram_chat_id"),
            "wechat_id": wechat_id,
            "notification_email": preferences.notification_email if preferences.notification_email is not None else existing.get("notification_email", user.email)
        }

        # Validate: if enabling telegram, chat_id must be set
        if update_data["telegram_alerts"] and not update_data["telegram_chat_id"]:
            raise HTTPException(
                status_code=400,
                detail="Telegram Chat ID is required when enabling Telegram alerts"
            )

        # Save preferences
        success = manager.save_notification_preferences(update_data)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save notification preferences"
            )

        # Add wechat_openid for backward compatibility
        response_data = {**update_data, "wechat_openid": update_data.get("wechat_id")}
        return NotificationPreferencesResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update notification preferences: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update notification preferences"
        )


@router.post("/notifications/test", response_model=TestNotificationResponse)
async def test_notification(
    request: TestNotificationRequest,
    user: UserInfo = Depends(get_current_user)
) -> TestNotificationResponse:
    """
    Send a test notification to verify configuration.

    Args:
        request: Contains channel ('email', 'telegram', or 'wechat')

    Returns:
        Success status and message
    """
    manager = get_airtable_manager()
    prefs = manager.get_notification_preferences(user.email)

    test_message = f"This is a test notification from WinningCV for {user.email}"

    if request.channel == "email":
        target_email = prefs.get("notification_email") or user.email
        success = send_email_notification(
            subject="WinningCV Test Notification",
            body=f"Hi!\n\n{test_message}\n\nIf you received this email, your notification settings are working correctly.\n\n- The WinningCV Team",
            to_email=target_email
        )
        return TestNotificationResponse(
            success=success,
            channel="email",
            message=f"Test email sent to {target_email}" if success else "Failed to send test email. Check SMTP configuration."
        )

    elif request.channel == "telegram":
        chat_id = prefs.get("telegram_chat_id")
        if not chat_id:
            return TestNotificationResponse(
                success=False,
                channel="telegram",
                message="Telegram Chat ID not configured. Please set your Chat ID first."
            )

        success = send_telegram_to_user(
            message=f"*WinningCV Test Notification*\n\n{test_message}\n\nIf you received this message, your Telegram alerts are working!",
            chat_id=chat_id
        )
        return TestNotificationResponse(
            success=success,
            channel="telegram",
            message="Test message sent to Telegram" if success else "Failed to send Telegram message. Check your Chat ID and bot configuration."
        )

    elif request.channel == "wechat":
        wechat_id = prefs.get("wechat_id") or prefs.get("wechat_openid")
        if not wechat_id:
            return TestNotificationResponse(
                success=False,
                channel="wechat",
                message="WeChat ID not configured. Please set your WeChat ID first."
            )

        success = send_wechat_message(
            message=f"**WinningCV Test Notification**\n\n{test_message}\n\nIf you received this message, your WeChat alerts are working!",
            wechat_id=wechat_id
        )
        return TestNotificationResponse(
            success=success,
            channel="wechat",
            message="Test message sent to WeChat" if success else "Failed to send WeChat message. Check WeChat configuration."
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel '{request.channel}'. Supported: email, telegram, wechat"
        )
