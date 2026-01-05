"""
Authentication middleware for WinningCV API.
Supports both token-based auth (like sel-exam) and session cookies.
"""
import os
import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyCookie, APIKeyHeader
import httpx

from api.schemas.auth import UserInfo

logger = logging.getLogger(__name__)

# Auth service configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://ai-video-backend.jackhui.com.au")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "sessionid")
CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "csrftoken")

# Security schemes
session_cookie = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)
auth_header = APIKeyHeader(name="Authorization", auto_error=False)


class AuthMiddleware:
    """Middleware to verify authentication with external auth service"""

    def __init__(self, auth_service_url: str = AUTH_SERVICE_URL):
        self.auth_service_url = auth_service_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def verify_token(self, token: str) -> Optional[UserInfo]:
        """
        Verify auth token with auth service and return user info.
        This is the primary auth method (like sel-exam).

        Args:
            token: Auth token (from Authorization header)

        Returns:
            UserInfo if authenticated, None otherwise
        """
        if not token:
            return None

        try:
            client = await self.get_client()

            # Call auth service's user info endpoint with token
            response = await client.get(
                f"{self.auth_service_url}/api/sehs/user-info/",
                headers={
                    "Authorization": f"Token {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            )

            if response.status_code == 200:
                data = response.json()
                return UserInfo(**data)
            elif response.status_code == 401:
                logger.debug("Token not authenticated")
                return None
            else:
                logger.warning(f"Auth service returned {response.status_code}")
                return None

        except httpx.RequestError as e:
            logger.error(f"Failed to verify token: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None

    async def verify_session(self, session_id: str, csrf_token: Optional[str] = None) -> Optional[UserInfo]:
        """
        Verify session with auth service and return user info.
        This is the fallback auth method (session cookies).

        Args:
            session_id: Session cookie value
            csrf_token: Optional CSRF token for additional verification

        Returns:
            UserInfo if authenticated, None otherwise
        """
        if not session_id:
            return None

        try:
            client = await self.get_client()

            # Build cookies dict
            cookies = {SESSION_COOKIE_NAME: session_id}
            if csrf_token:
                cookies[CSRF_COOKIE_NAME] = csrf_token

            # Call auth service's user info endpoint
            response = await client.get(
                f"{self.auth_service_url}/api/sehs/user-info/",
                cookies=cookies,
                headers={
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                }
            )

            if response.status_code == 200:
                data = response.json()
                return UserInfo(**data)
            elif response.status_code == 401:
                logger.debug("Session not authenticated")
                return None
            else:
                logger.warning(f"Auth service returned {response.status_code}")
                return None

        except httpx.RequestError as e:
            logger.error(f"Failed to verify session: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying session: {e}")
            return None

    async def close(self):
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global auth middleware instance
auth_middleware = AuthMiddleware()


def extract_token(authorization: Optional[str]) -> Optional[str]:
    """Extract token from Authorization header"""
    if not authorization:
        return None

    # Support both "Token <token>" and "Bearer <token>" formats
    if authorization.startswith("Token "):
        return authorization[6:]
    elif authorization.startswith("Bearer "):
        return authorization[7:]

    return None


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Depends(auth_header),
    session_id: Optional[str] = Depends(session_cookie)
) -> UserInfo:
    """
    Dependency to get the current authenticated user.
    Supports both token-based auth (primary) and session cookies (fallback).
    Raises HTTPException 401 if not authenticated.
    """
    # Try token-based auth first (like sel-exam)
    token = extract_token(authorization)
    if token:
        user = await auth_middleware.verify_token(token)
        if user:
            return user

    # Fallback to session cookie auth
    if session_id:
        csrf_token = request.cookies.get(CSRF_COOKIE_NAME)
        user = await auth_middleware.verify_session(session_id, csrf_token)
        if user:
            return user

    # Neither method worked
    raise HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer, Cookie"}
    )


async def get_optional_user(
    request: Request,
    authorization: Optional[str] = Depends(auth_header),
    session_id: Optional[str] = Depends(session_cookie)
) -> Optional[UserInfo]:
    """
    Dependency to optionally get the current user.
    Returns None if not authenticated (doesn't raise exception).
    """
    # Try token-based auth first
    token = extract_token(authorization)
    if token:
        user = await auth_middleware.verify_token(token)
        if user:
            return user

    # Fallback to session cookie auth
    if session_id:
        csrf_token = request.cookies.get(CSRF_COOKIE_NAME)
        user = await auth_middleware.verify_session(session_id, csrf_token)
        if user:
            return user

    return None
