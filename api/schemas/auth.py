from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserInfo(BaseModel):
    """User information from auth service"""
    auth_user_id: int
    email: EmailStr
    display_name: str
    provider: str
    is_verified: bool
    is_staff: bool = False
    is_superuser: bool = False
    date_joined: Optional[datetime] = None
    last_login: Optional[datetime] = None


class AuthStatus(BaseModel):
    """Authentication status response"""
    is_authenticated: bool
    user: Optional[UserInfo] = None


class CSRFToken(BaseModel):
    """CSRF token response"""
    csrf_token: str
