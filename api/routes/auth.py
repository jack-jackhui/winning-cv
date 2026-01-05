"""
Authentication routes for WinningCV API.
Proxies auth requests to external auth service.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import httpx

from api.schemas.auth import AuthStatus, UserInfo, CSRFToken
from api.middleware.auth_middleware import get_current_user, get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://ai-video-backend.jackhui.com.au")


@router.get("/me", response_model=AuthStatus)
async def get_auth_status(
    user: Optional[UserInfo] = Depends(get_optional_user)
) -> AuthStatus:
    """
    Get current authentication status.
    Returns user info if authenticated, or is_authenticated=False otherwise.
    """
    return AuthStatus(
        is_authenticated=user is not None,
        user=user
    )


@router.get("/user", response_model=UserInfo)
async def get_user_info(
    user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """
    Get current user information.
    Requires authentication.
    """
    return user


@router.get("/csrf", response_model=CSRFToken)
async def get_csrf_token(request: Request) -> CSRFToken:
    """
    Get CSRF token from auth service.
    This proxies the request to the auth service's CSRF endpoint.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Forward cookies to auth service
            cookies = dict(request.cookies)

            response = await client.get(
                f"{AUTH_SERVICE_URL}/api/csrf/",
                cookies=cookies
            )

            if response.status_code == 200:
                data = response.json()
                return CSRFToken(csrf_token=data.get("csrfToken", ""))
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to get CSRF token"
                )
    except httpx.RequestError as e:
        logger.error(f"Failed to get CSRF token: {e}")
        raise HTTPException(
            status_code=503,
            detail="Auth service unavailable"
        )


@router.get("/login-url")
async def get_login_url(
    provider: str = "google",
    redirect_uri: Optional[str] = None
) -> dict:
    """
    Get the OAuth login URL for the specified provider.

    Args:
        provider: OAuth provider (google, microsoft, github)
        redirect_uri: Optional redirect URI after login

    Returns:
        Dictionary with login_url
    """
    # Build the OAuth login URL
    base_url = AUTH_SERVICE_URL.rstrip("/")

    # Use allauth's browser-based OAuth flow (redirects to provider)
    provider_endpoints = {
        "google": "/accounts/google/login/",
        "microsoft": "/accounts/microsoft/login/",
        "github": "/accounts/github/login/",
    }

    if provider not in provider_endpoints:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Supported: {list(provider_endpoints.keys())}"
        )

    login_url = f"{base_url}{provider_endpoints[provider]}"

    return {
        "provider": provider,
        "login_url": login_url,
        "auth_service_url": base_url
    }


@router.post("/logout")
async def logout(
    request: Request,
    user: UserInfo = Depends(get_current_user)
) -> dict:
    """
    Logout the current user by invalidating the session.
    Proxies the logout request to the auth service.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            cookies = dict(request.cookies)

            # Get CSRF token for POST request
            csrf_token = cookies.get("csrftoken", "")

            response = await client.post(
                f"{AUTH_SERVICE_URL}/api/dj-rest-auth/logout/",
                cookies=cookies,
                headers={
                    "X-CSRFToken": csrf_token,
                    "Content-Type": "application/json"
                }
            )

            if response.status_code in [200, 204]:
                return {"message": "Logged out successfully"}
            else:
                logger.warning(f"Logout returned {response.status_code}")
                return {"message": "Logout processed"}

    except httpx.RequestError as e:
        logger.error(f"Failed to logout: {e}")
        # Still return success to frontend
        return {"message": "Logged out locally"}
