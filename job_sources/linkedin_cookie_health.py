"""
LinkedIn Cookie Health Monitor

Monitors the health of LinkedIn session cookies using ACTUAL SESSION VALIDATION
instead of arbitrary age-based thresholds.

This module provides:
1. Session-based validity testing (the source of truth)
2. Cached session status to avoid redundant browser startups
3. Alert notifications via Telegram/Email when session is truly invalid
4. Pre-job validation for cron jobs
5. Integration with APScheduler for periodic checks
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from enum import Enum
from pathlib import Path

from job_sources.linkedin_cookie_manager import get_cookie_manager
from utils.notifications import send_telegram_message, send_email_notification
from config.settings import Config

logger = logging.getLogger(__name__)


class CookieStatus(Enum):
    """Cookie health status levels - now based on actual session validity"""
    HEALTHY = "healthy"       # Session is valid and authenticated
    INVALID = "invalid"       # Session test failed - needs refresh
    MISSING = "missing"       # No cookies found
    UNTESTED = "untested"     # Cookies exist but session not yet tested


# Cache file for session test results
SESSION_CACHE_FILE = Path("cookies/session_status_cache.json")


def _load_session_cache() -> Optional[Dict]:
    """Load cached session test result."""
    try:
        if SESSION_CACHE_FILE.exists():
            with open(SESSION_CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load session cache: {e}")
    return None


def _save_session_cache(is_valid: bool, message: str):
    """Save session test result to cache."""
    try:
        SESSION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "is_valid": is_valid,
            "message": message,
            "tested_at": datetime.now().isoformat(),
        }
        with open(SESSION_CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        logger.debug(f"Session cache saved: valid={is_valid}")
    except Exception as e:
        logger.warning(f"Could not save session cache: {e}")


def _is_cache_valid(max_age_hours: int = 24) -> bool:
    """Check if cached session result is still valid (not too old)."""
    cache = _load_session_cache()
    if not cache:
        return False

    try:
        tested_at = datetime.fromisoformat(cache['tested_at'])
        age = datetime.now() - tested_at
        return age < timedelta(hours=max_age_hours)
    except (KeyError, ValueError):
        return False


def test_cookie_session(force: bool = False) -> Tuple[bool, str]:
    """
    Test if the cookie session is actually valid by attempting to load LinkedIn.

    This is the SOURCE OF TRUTH for cookie health - not the cookie age.
    Results are cached for 24 hours to avoid redundant browser startups.

    Args:
        force: If True, bypass cache and perform fresh test

    Returns:
        Tuple of (is_valid, message)
    """
    # Check cache first (unless forced)
    if not force and _is_cache_valid(max_age_hours=24):
        cache = _load_session_cache()
        logger.info(f"Using cached session status: valid={cache['is_valid']}")
        return cache['is_valid'], f"[Cached] {cache['message']}"

    logger.info("Performing fresh session validity test...")

    try:
        from job_sources.linkedin_job_scraper import LinkedInJobScraper

        scraper = LinkedInJobScraper()
        is_valid = scraper.has_valid_session

        # Clean up browser
        try:
            if scraper.browser:
                scraper.browser.quit()
        except Exception as cleanup_error:
            logger.debug(f"Browser cleanup: {cleanup_error}")

        if is_valid:
            message = "Session is valid and authenticated."
            _save_session_cache(True, message)
            return True, message
        else:
            message = "Session is not authenticated. Cookies need refresh."
            _save_session_cache(False, message)
            return False, message

    except Exception as e:
        logger.error(f"Error testing cookie session: {e}")
        message = f"Could not test session: {str(e)}"
        # Don't cache errors - let it retry next time
        return False, message


def check_cookie_health(use_session_test: bool = True, force_test: bool = False) -> Dict:
    """
    Check the health status of LinkedIn cookies.

    Now uses ACTUAL SESSION VALIDATION as the primary health indicator,
    not arbitrary age-based thresholds.

    Args:
        use_session_test: If True, use cached session test result for status
        force_test: If True, force a fresh session test (ignores cache)

    Returns:
        Dictionary with cookie health information:
        - status: CookieStatus enum value
        - session_valid: Boolean indicating actual session validity
        - age_days: Number of days since cookies were saved (informational only)
        - age_hours: Total hours since cookies were saved
        - saved_at: ISO timestamp when cookies were saved
        - cookie_count: Number of cookies stored
        - message: Human-readable status message
        - needs_refresh: Boolean indicating if refresh is required
        - last_tested: When session was last tested
    """
    cm = get_cookie_manager()

    # Check if cookies exist
    if not cm.has_cookies():
        return {
            "status": CookieStatus.MISSING,
            "session_valid": False,
            "age_days": None,
            "age_hours": None,
            "saved_at": None,
            "cookie_count": 0,
            "message": "No LinkedIn cookies found. Login required.",
            "needs_refresh": True,
            "last_tested": None
        }

    # Get cookie info
    info = cm.get_cookie_info()
    if not info:
        return {
            "status": CookieStatus.MISSING,
            "session_valid": False,
            "age_days": None,
            "age_hours": None,
            "saved_at": None,
            "cookie_count": 0,
            "message": "Could not read cookie information.",
            "needs_refresh": True,
            "last_tested": None
        }

    # Calculate age (informational only - not used for status determination)
    age_days = None
    age_hours = None
    try:
        saved_at = datetime.fromisoformat(info['saved_at'])
        age = datetime.now() - saved_at
        age_days = age.days
        age_hours = age.total_seconds() / 3600
    except (KeyError, ValueError) as e:
        logger.warning(f"Error parsing cookie timestamp: {e}")

    # Determine status based on SESSION VALIDITY (not age!)
    last_tested = None
    if use_session_test:
        # Check cached session status
        cache = _load_session_cache()
        if cache:
            last_tested = cache.get('tested_at')

        if force_test or not _is_cache_valid(max_age_hours=24):
            # Need to run fresh test
            is_valid, session_msg = test_cookie_session(force=force_test)
            cache = _load_session_cache()
            if cache:
                last_tested = cache.get('tested_at')
        else:
            # Use cached result
            is_valid = cache.get('is_valid', False)
            session_msg = cache.get('message', 'Cached result')

        if is_valid:
            status = CookieStatus.HEALTHY
            age_info = f" (cookies are {age_days} days old)" if age_days else ""
            message = f"Session is valid and authenticated{age_info}."
            needs_refresh = False
        else:
            status = CookieStatus.INVALID
            message = f"Session validation failed. {session_msg}"
            needs_refresh = True
    else:
        # Session test not requested - just report cookies exist
        status = CookieStatus.UNTESTED
        message = f"Cookies exist ({age_days} days old) but session not validated."
        needs_refresh = False  # Unknown - need to test

    return {
        "status": status,
        "session_valid": status == CookieStatus.HEALTHY,
        "age_days": age_days,
        "age_hours": round(age_hours, 1) if age_hours else None,
        "saved_at": info.get('saved_at'),
        "cookie_count": info.get('cookie_count', 0),
        "message": message,
        "needs_refresh": needs_refresh,
        "last_tested": last_tested
    }


def send_cookie_alert(health_info: Dict):
    """
    Send alert notifications about cookie health status.

    Args:
        health_info: Dictionary from check_cookie_health()
    """
    status = health_info['status']

    # Only send alerts when session is actually invalid or missing
    if status == CookieStatus.HEALTHY:
        logger.info(f"Cookie session is valid, no alert needed.")
        return

    if status == CookieStatus.UNTESTED:
        logger.info(f"Cookie session untested, no alert sent.")
        return

    # Build alert message
    emoji_map = {
        CookieStatus.INVALID: "🔴",
        CookieStatus.MISSING: "❌",
    }

    emoji = emoji_map.get(status, "⚠️")

    message_parts = [
        f"{emoji} **LinkedIn Cookie Alert**",
        "",
        f"**Status:** {status.value.upper()}",
        f"**Message:** {health_info['message']}",
    ]

    if health_info['age_days'] is not None:
        message_parts.append(f"**Cookie Age:** {health_info['age_days']} days")

    if health_info['last_tested']:
        message_parts.append(f"**Last Tested:** {health_info['last_tested']}")

    message_parts.extend([
        "",
        "**Action Required:**",
        "1. Run `python -m job_sources.linkedin_login` on your local machine",
        "2. Run `./scripts/sync_linkedin_cookies.sh` to sync to production",
    ])

    message = "\n".join(message_parts)

    # Send via Telegram (primary)
    try:
        send_telegram_message(message)
        logger.info("Cookie alert sent via Telegram")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")

    # Send via Email (backup)
    try:
        subject = f"WinningCV: LinkedIn Cookie {status.value.upper()}"
        email_body = message.replace("**", "").replace("*", "")
        send_email_notification(subject, email_body)
        logger.info("Cookie alert sent via Email")
    except Exception as e:
        logger.error(f"Failed to send Email alert: {e}")


def run_cookie_health_check(send_alert: bool = True, force_test: bool = False) -> Dict:
    """
    Run a complete cookie health check using session validation.

    This is the main function to be called by the scheduler or before jobs.

    Args:
        send_alert: Whether to send alert notifications for issues
        force_test: Whether to force a fresh session test (ignores cache)

    Returns:
        Health check result dictionary
    """
    logger.info("Running LinkedIn cookie health check...")

    health_info = check_cookie_health(use_session_test=True, force_test=force_test)

    logger.info(f"Cookie status: {health_info['status'].value}")
    logger.info(f"Session valid: {health_info['session_valid']}")
    logger.info(f"Message: {health_info['message']}")

    if send_alert and health_info['needs_refresh']:
        send_cookie_alert(health_info)

    return health_info


def validate_session_for_job() -> Tuple[bool, str]:
    """
    Validate session before running a job. This should be called by cron jobs
    before starting the job runner.

    Uses cached session status if available and recent (< 24 hours).
    Only performs fresh test if cache is stale or missing.

    Returns:
        Tuple of (can_proceed, message)
    """
    logger.info("Validating LinkedIn session for job...")

    cm = get_cookie_manager()

    # Check if cookies exist at all
    if not cm.has_cookies():
        return False, "No LinkedIn cookies found. Cannot proceed."

    # Check session validity (uses cache if available)
    is_valid, message = test_cookie_session(force=False)

    if is_valid:
        logger.info("Session validation passed. Job can proceed.")
        return True, "Session is valid. Job can proceed."
    else:
        logger.warning(f"Session validation failed: {message}")
        # Send alert
        health_info = check_cookie_health(use_session_test=True, force_test=False)
        send_cookie_alert(health_info)
        return False, f"Session invalid: {message}. Alert sent."


# Scheduler integration
_scheduler_job_id = "linkedin_cookie_health_check"


def schedule_cookie_health_check(scheduler, interval_hours: int = 24):
    """
    Schedule periodic cookie health checks.

    With session-based detection, daily checks are sufficient since
    we test actual session validity, not arbitrary age thresholds.

    Args:
        scheduler: APScheduler BackgroundScheduler instance
        interval_hours: How often to run checks (default: 24 hours)
    """
    from apscheduler.triggers.interval import IntervalTrigger

    # Remove existing job if any
    try:
        scheduler.remove_job(_scheduler_job_id)
    except:
        pass

    # Add new job - force fresh test on scheduled runs
    def scheduled_check():
        return run_cookie_health_check(send_alert=True, force_test=True)

    scheduler.add_job(
        scheduled_check,
        trigger=IntervalTrigger(hours=interval_hours),
        id=_scheduler_job_id,
        name="LinkedIn Cookie Health Check",
        max_instances=1,
        replace_existing=True
    )

    logger.info(f"Scheduled cookie health check every {interval_hours} hours")


# Legacy function - kept for backwards compatibility
def get_check_interval_hours() -> int:
    """
    Get the recommended check interval.

    With session-based detection, we use a fixed 24-hour interval
    since we're testing actual validity, not guessing based on age.

    Returns:
        Interval in hours (always 24 with session-based detection)
    """
    return 24


# Legacy function - kept for backwards compatibility
def setup_adaptive_cookie_monitoring(scheduler):
    """
    Set up cookie monitoring. Now uses fixed daily interval since
    session-based detection doesn't need adaptive frequency.

    Args:
        scheduler: APScheduler BackgroundScheduler instance
    """
    schedule_cookie_health_check(scheduler, interval_hours=24)
    logger.info("Set up daily session-based cookie monitoring")


if __name__ == "__main__":
    # Allow running as standalone script for testing
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("LinkedIn Cookie Health Check (Session-Based)")
    print("=" * 60)

    force = "--force" in sys.argv

    # Run health check
    health = run_cookie_health_check(
        send_alert="--alert" in sys.argv,
        force_test=force
    )

    print()
    print(f"Status:         {health['status'].value}")
    print(f"Session Valid:  {health['session_valid']}")
    print(f"Message:        {health['message']}")
    print(f"Age:            {health['age_days']} days" if health['age_days'] else "Age: N/A")
    print(f"Cookie Count:   {health['cookie_count']}")
    print(f"Saved At:       {health['saved_at']}")
    print(f"Needs Refresh:  {health['needs_refresh']}")
    print(f"Last Tested:    {health['last_tested']}")
    print()

    if "--validate-job" in sys.argv:
        print("=" * 60)
        print("Pre-Job Validation")
        print("=" * 60)
        can_proceed, msg = validate_session_for_job()
        print(f"Can Proceed: {can_proceed}")
        print(f"Message: {msg}")
        sys.exit(0 if can_proceed else 1)

    if "--alert" in sys.argv:
        print("Alert sent (if status required it)")
