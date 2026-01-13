"""
LinkedIn Cookie Health Monitor

Monitors the health of LinkedIn session cookies and sends alerts
when cookies are expired or about to expire.

This module provides:
1. Cookie age checking
2. Session validity testing
3. Alert notifications via Telegram/Email
4. Integration with APScheduler for periodic checks
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from enum import Enum

from job_sources.linkedin_cookie_manager import get_cookie_manager
from utils.notifications import send_telegram_message, send_email_notification
from config.settings import Config

logger = logging.getLogger(__name__)


class CookieStatus(Enum):
    """Cookie health status levels"""
    HEALTHY = "healthy"       # < 3 days old
    AGING = "aging"           # 3-5 days old
    STALE = "stale"           # 5-7 days old
    EXPIRED = "expired"       # > 7 days old
    MISSING = "missing"       # No cookies found
    INVALID = "invalid"       # Cookies exist but session invalid


# Thresholds in days
COOKIE_THRESHOLDS = {
    "healthy": 3,
    "aging": 5,
    "stale": 7,
}


def check_cookie_health() -> Dict:
    """
    Check the health status of LinkedIn cookies.

    Returns:
        Dictionary with cookie health information:
        - status: CookieStatus enum value
        - age_days: Number of days since cookies were saved
        - age_hours: Total hours since cookies were saved
        - saved_at: ISO timestamp when cookies were saved
        - cookie_count: Number of cookies stored
        - message: Human-readable status message
        - needs_refresh: Boolean indicating if refresh is recommended
    """
    cm = get_cookie_manager()

    # Check if cookies exist
    if not cm.has_cookies():
        return {
            "status": CookieStatus.MISSING,
            "age_days": None,
            "age_hours": None,
            "saved_at": None,
            "cookie_count": 0,
            "message": "No LinkedIn cookies found. Login required.",
            "needs_refresh": True
        }

    # Get cookie info
    info = cm.get_cookie_info()
    if not info:
        return {
            "status": CookieStatus.INVALID,
            "age_days": None,
            "age_hours": None,
            "saved_at": None,
            "cookie_count": 0,
            "message": "Could not read cookie information.",
            "needs_refresh": True
        }

    # Calculate age
    try:
        saved_at = datetime.fromisoformat(info['saved_at'])
        age = datetime.now() - saved_at
        age_days = age.days
        age_hours = age.total_seconds() / 3600
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing cookie timestamp: {e}")
        return {
            "status": CookieStatus.INVALID,
            "age_days": None,
            "age_hours": None,
            "saved_at": info.get('saved_at'),
            "cookie_count": info.get('cookie_count', 0),
            "message": "Invalid cookie timestamp.",
            "needs_refresh": True
        }

    # Determine status based on age
    if age_days >= COOKIE_THRESHOLDS["stale"]:
        status = CookieStatus.EXPIRED
        message = f"Cookies are {age_days} days old. Refresh required!"
        needs_refresh = True
    elif age_days >= COOKIE_THRESHOLDS["aging"]:
        status = CookieStatus.STALE
        message = f"Cookies are {age_days} days old. Refresh recommended soon."
        needs_refresh = True
    elif age_days >= COOKIE_THRESHOLDS["healthy"]:
        status = CookieStatus.AGING
        message = f"Cookies are {age_days} days old. Still valid but aging."
        needs_refresh = False
    else:
        status = CookieStatus.HEALTHY
        message = f"Cookies are fresh ({age_days} days, {int(age_hours % 24)} hours old)."
        needs_refresh = False

    return {
        "status": status,
        "age_days": age_days,
        "age_hours": round(age_hours, 1),
        "saved_at": info['saved_at'],
        "cookie_count": info.get('cookie_count', 0),
        "message": message,
        "needs_refresh": needs_refresh
    }


def test_cookie_session() -> Tuple[bool, str]:
    """
    Test if the cookie session is actually valid by attempting to load LinkedIn.

    This is a more thorough check that verifies the session works, not just
    that cookies exist.

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        from job_sources.linkedin_job_scraper import LinkedInJobScraper

        scraper = LinkedInJobScraper()
        is_valid = scraper.has_valid_session

        # Clean up
        try:
            scraper.browser.quit()
        except:
            pass

        if is_valid:
            return True, "Session is valid and authenticated."
        else:
            return False, "Session is not authenticated. Cookies may be expired."

    except Exception as e:
        logger.error(f"Error testing cookie session: {e}")
        return False, f"Could not test session: {str(e)}"


def send_cookie_alert(health_info: Dict, include_session_test: bool = False):
    """
    Send alert notifications about cookie health status.

    Args:
        health_info: Dictionary from check_cookie_health()
        include_session_test: Whether to include session validity test
    """
    status = health_info['status']

    # Only send alerts for problematic statuses
    if status in [CookieStatus.HEALTHY, CookieStatus.AGING]:
        logger.info(f"Cookie status is {status.value}, no alert needed.")
        return

    # Build alert message
    emoji_map = {
        CookieStatus.STALE: "⚠️",
        CookieStatus.EXPIRED: "🔴",
        CookieStatus.MISSING: "❌",
        CookieStatus.INVALID: "❌",
    }

    emoji = emoji_map.get(status, "⚠️")

    message_parts = [
        f"{emoji} **LinkedIn Cookie Alert**",
        "",
        f"**Status:** {status.value.upper()}",
        f"**Message:** {health_info['message']}",
    ]

    if health_info['age_days'] is not None:
        message_parts.append(f"**Age:** {health_info['age_days']} days, {int(health_info['age_hours'] % 24)} hours")

    if health_info['cookie_count']:
        message_parts.append(f"**Cookie Count:** {health_info['cookie_count']}")

    if health_info['saved_at']:
        message_parts.append(f"**Saved At:** {health_info['saved_at']}")

    # Optional session test
    if include_session_test:
        is_valid, session_msg = test_cookie_session()
        message_parts.extend([
            "",
            f"**Session Test:** {'✅ Valid' if is_valid else '❌ Invalid'}",
            f"**Details:** {session_msg}"
        ])

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
        # Convert markdown to plain text for email
        email_body = message.replace("**", "").replace("*", "")
        send_email_notification(subject, email_body)
        logger.info("Cookie alert sent via Email")
    except Exception as e:
        logger.error(f"Failed to send Email alert: {e}")


def run_cookie_health_check(send_alert: bool = True, test_session: bool = False):
    """
    Run a complete cookie health check and optionally send alerts.

    This is the main function to be called by the scheduler.

    Args:
        send_alert: Whether to send alert notifications for issues
        test_session: Whether to perform actual session validity test
                     (more thorough but slower)

    Returns:
        Health check result dictionary
    """
    logger.info("Running LinkedIn cookie health check...")

    health_info = check_cookie_health()

    logger.info(f"Cookie status: {health_info['status'].value}")
    logger.info(f"Message: {health_info['message']}")

    if send_alert and health_info['needs_refresh']:
        send_cookie_alert(health_info, include_session_test=test_session)

    return health_info


def get_check_interval_hours() -> int:
    """
    Get the recommended check interval based on cookie age.

    Returns more frequent checks as cookies get older.

    Returns:
        Interval in hours
    """
    health_info = check_cookie_health()
    status = health_info['status']

    if status == CookieStatus.HEALTHY:
        return 24  # Check once a day when healthy
    elif status == CookieStatus.AGING:
        return 12  # Check twice a day when aging
    elif status == CookieStatus.STALE:
        return 6   # Check every 6 hours when stale
    else:
        return 4   # Check every 4 hours when expired/missing


# Scheduler integration
_scheduler_job_id = "linkedin_cookie_health_check"


def schedule_cookie_health_check(scheduler, interval_hours: int = 12):
    """
    Schedule periodic cookie health checks.

    Args:
        scheduler: APScheduler BackgroundScheduler instance
        interval_hours: How often to run checks (default: 12 hours)
    """
    from apscheduler.triggers.interval import IntervalTrigger

    # Remove existing job if any
    try:
        scheduler.remove_job(_scheduler_job_id)
    except:
        pass

    # Add new job
    scheduler.add_job(
        run_cookie_health_check,
        trigger=IntervalTrigger(hours=interval_hours),
        id=_scheduler_job_id,
        name="LinkedIn Cookie Health Check",
        max_instances=1,
        replace_existing=True
    )

    logger.info(f"Scheduled cookie health check every {interval_hours} hours")


def setup_adaptive_cookie_monitoring(scheduler):
    """
    Set up adaptive cookie monitoring that adjusts check frequency
    based on cookie age.

    This runs an initial check and schedules future checks at
    appropriate intervals.

    Args:
        scheduler: APScheduler BackgroundScheduler instance
    """
    from apscheduler.triggers.interval import IntervalTrigger

    def adaptive_check():
        """Run check and reschedule based on result"""
        health_info = run_cookie_health_check(send_alert=True, test_session=False)

        # Get new interval
        new_interval = get_check_interval_hours()

        # Reschedule with new interval
        try:
            job = scheduler.get_job(_scheduler_job_id)
            if job:
                current_interval = job.trigger.interval.total_seconds() / 3600
                if current_interval != new_interval:
                    scheduler.reschedule_job(
                        _scheduler_job_id,
                        trigger=IntervalTrigger(hours=new_interval)
                    )
                    logger.info(f"Rescheduled cookie check: {current_interval}h -> {new_interval}h")
        except Exception as e:
            logger.error(f"Failed to reschedule job: {e}")

    # Initial check
    adaptive_check()

    # Schedule adaptive checks
    initial_interval = get_check_interval_hours()
    scheduler.add_job(
        adaptive_check,
        trigger=IntervalTrigger(hours=initial_interval),
        id=_scheduler_job_id,
        name="LinkedIn Cookie Health Check (Adaptive)",
        max_instances=1,
        replace_existing=True
    )

    logger.info(f"Set up adaptive cookie monitoring (initial interval: {initial_interval}h)")


if __name__ == "__main__":
    # Allow running as standalone script for testing
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("LinkedIn Cookie Health Check")
    print("=" * 60)

    # Run health check
    health = run_cookie_health_check(
        send_alert="--alert" in sys.argv,
        test_session="--test-session" in sys.argv
    )

    print()
    print(f"Status:        {health['status'].value}")
    print(f"Message:       {health['message']}")
    print(f"Age:           {health['age_days']} days, {int(health['age_hours'] % 24) if health['age_hours'] else 0} hours")
    print(f"Cookie Count:  {health['cookie_count']}")
    print(f"Saved At:      {health['saved_at']}")
    print(f"Needs Refresh: {health['needs_refresh']}")
    print()

    if "--alert" in sys.argv:
        print("Alert sent (if status required it)")
