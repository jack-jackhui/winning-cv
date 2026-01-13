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

# HTTP client configuration
HTTP_TIMEOUT = httpx.Timeout(
    connect=5.0,    # Connection timeout
    read=10.0,      # Read timeout
    write=5.0,      # Write timeout
    pool=5.0        # Pool timeout
)
HTTP_LIMITS = httpx.Limits(
    max_keepalive_connections=5,
    max_connections=10,
    keepalive_expiry=30.0  # Close idle connections after 30s
)


class AuthMiddleware:
    """Middleware to verify authentication with external auth service"""

    def __init__(self, auth_service_url: str = AUTH_SERVICE_URL):
        self.auth_service_url = auth_service_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with proper connection management"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                limits=HTTP_LIMITS,
            )
        return self._client

    async def _reset_client(self):
        """Reset client to recover from connection errors"""
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception:
                pass
        self._client = None

    async def _make_auth_request(
        self,
        headers: dict,
        cookies: Optional[dict] = None,
        max_retries: int = 2
    ) -> Optional[httpx.Response]:
        """
        Make auth request with retry on connection errors.

        Handles "Server disconnected without sending a response" by
        resetting the client and retrying with a fresh connection.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                client = await self.get_client()
                response = await client.get(
                    f"{self.auth_service_url}/api/sehs/user-info/",
                    headers=headers,
                    cookies=cookies or {},
                )
                return response

            except (httpx.RemoteProtocolError, httpx.ReadError) as e:
                # Connection was closed by server - reset and retry
                last_error = e
                logger.warning(f"Auth request connection error (attempt {attempt + 1}): {e}")
                await self._reset_client()
                continue

            except httpx.RequestError as e:
                last_error = e
                logger.error(f"Auth request failed: {e}")
                break

        if last_error:
            logger.error(f"Auth request failed after {max_retries} attempts: {last_error}")
        return None

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
            response = await self._make_auth_request(
                headers={
                    "Authorization": f"Token {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            )

            if response is None:
                return None

            if response.status_code == 200:
                data = response.json()
                return UserInfo(**data)
            elif response.status_code == 401:
                logger.debug("Token not authenticated")
                return None
            else:
                logger.warning(f"Auth service returned {response.status_code}")
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
            # Build cookies dict
            cookies = {SESSION_COOKIE_NAME: session_id}
            if csrf_token:
                cookies[CSRF_COOKIE_NAME] = csrf_token

            response = await self._make_auth_request(
                headers={
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                cookies=cookies,
            )

            if response is None:
                return None

            if response.status_code == 200:
                data = response.json()
                return UserInfo(**data)
            elif response.status_code == 401:
                logger.debug("Session not authenticated")
                return None
            else:
                logger.warning(f"Auth service returned {response.status_code}")
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
