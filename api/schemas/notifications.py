"""
Notification preferences schemas for WinningCV API.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class NotificationPreferences(BaseModel):
    """User notification preferences"""
    email_alerts: bool = True
    telegram_alerts: bool = False
    wechat_alerts: bool = False
    weekly_digest: bool = True
    telegram_chat_id: Optional[str] = None
    wechat_openid: Optional[str] = None
    notification_email: Optional[str] = None


class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences request"""
    email_alerts: Optional[bool] = None
    telegram_alerts: Optional[bool] = None
    wechat_alerts: Optional[bool] = None
    weekly_digest: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    wechat_openid: Optional[str] = None
    notification_email: Optional[str] = None


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response with user email"""
    user_email: str
    email_alerts: bool
    telegram_alerts: bool
    wechat_alerts: bool
    weekly_digest: bool
    telegram_chat_id: Optional[str] = None
    wechat_openid: Optional[str] = None
    notification_email: Optional[str] = None


class TestNotificationRequest(BaseModel):
    """Request to send a test notification"""
    channel: str  # 'email', 'telegram', or 'wechat'


class TestNotificationResponse(BaseModel):
    """Response from test notification"""
    success: bool
    channel: str
    message: str
