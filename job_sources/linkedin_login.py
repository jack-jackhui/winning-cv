#!/usr/bin/env python3
"""
LinkedIn Login Utility - Manual login with cookie persistence.

This script opens LinkedIn in a visible browser for manual authentication.
After successful login, it saves the session cookies for use by the scraper.

Usage:
    python -m job_sources.linkedin_login          # Interactive login
    python -m job_sources.linkedin_login --check  # Check cookie status
    python -m job_sources.linkedin_login --clear  # Clear saved cookies

The script will:
1. Open LinkedIn login page in a visible browser
2. Wait for you to log in (including MFA if required)
3. Save cookies after successful login
4. Close the browser

Subsequent scraping runs will use the saved cookies automatically.
"""

import sys
import time
import argparse
import logging
from DrissionPage import Chromium, ChromiumOptions
from config.settings import Config
from job_sources.linkedin_cookie_manager import get_cookie_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/"


def create_visible_browser() -> Chromium:
    """Create a visible (non-headless) browser for manual login."""
    options = ChromiumOptions()
    config = Config()

    options.auto_port(True) \
        .headless(False) \
        .no_imgs(False) \
        .mute(True) \
        .set_paths(browser_path=config.CHROMIUM_PATH or config.CHROME_PATH) \
        .set_user_agent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

    # Don't use incognito mode - we want to save session
    # options.incognito(False)

    if config.RUNNING_IN_DOCKER:
        logger.error("Cannot run interactive login in Docker. Run locally first.")
        sys.exit(1)

    return Chromium(options)


def wait_for_login(tab, timeout: int = 300) -> bool:
    """
    Wait for user to complete login.

    Args:
        tab: Browser tab to monitor
        timeout: Maximum wait time in seconds (default 5 minutes)

    Returns:
        True if login successful, False if timeout or error
    """
    logger.info(f"Waiting up to {timeout} seconds for login completion...")

    start_time = time.time()
    check_interval = 2  # Check every 2 seconds

    while time.time() - start_time < timeout:
        try:
            current_url = tab.url

            # Check if we've reached the feed or jobs page (login successful)
            if "/feed" in current_url or "/jobs" in current_url:
                logger.info("Login successful! Detected authenticated session.")
                return True

            # Check for LinkedIn home with session
            if current_url == "https://www.linkedin.com/" or current_url == "https://www.linkedin.com":
                # Additional check - look for session indicator
                try:
                    # Look for user's profile element or feed indicator
                    if tab.ele('@@class=feed-identity-module', timeout=1):
                        logger.info("Login successful! Found authenticated content.")
                        return True
                except:
                    pass

            time.sleep(check_interval)

        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            time.sleep(check_interval)

    logger.error(f"Login timeout after {timeout} seconds")
    return False


def extract_cookies(tab) -> list:
    """Extract cookies from browser tab."""
    try:
        # Get all cookies from the browser
        cookies = tab.cookies()
        if isinstance(cookies, dict):
            # Convert dict format to list format
            cookie_list = []
            for name, value in cookies.items():
                cookie_list.append({
                    "name": name,
                    "value": value,
                    "domain": ".linkedin.com"
                })
            return cookie_list
        return cookies if cookies else []
    except Exception as e:
        logger.error(f"Failed to extract cookies: {e}")
        return []


def interactive_login() -> bool:
    """
    Perform interactive LinkedIn login and save cookies.

    Returns:
        True if login successful and cookies saved, False otherwise.
    """
    browser = None
    try:
        logger.info("=" * 60)
        logger.info("LinkedIn Interactive Login")
        logger.info("=" * 60)
        logger.info("")
        logger.info("A browser window will open for you to log in to LinkedIn.")
        logger.info("Please complete the login process, including any MFA.")
        logger.info("The script will wait up to 5 minutes for you to log in.")
        logger.info("")
        logger.info("Starting browser...")

        browser = create_visible_browser()
        tab = browser.latest_tab

        # Navigate to LinkedIn login
        logger.info(f"Navigating to {LINKEDIN_LOGIN_URL}")
        tab.get(LINKEDIN_LOGIN_URL)
        time.sleep(2)

        # Wait for manual login
        print("\n" + "=" * 60)
        print("PLEASE LOG IN TO LINKEDIN IN THE BROWSER WINDOW")
        print("Complete any MFA/2FA verification if prompted")
        print("=" * 60 + "\n")

        if wait_for_login(tab, timeout=300):
            # Give it a moment to finalize session
            logger.info("Finalizing session...")
            time.sleep(3)

            # Navigate to jobs page to ensure we have all necessary cookies
            logger.info("Verifying access to LinkedIn Jobs...")
            tab.get(LINKEDIN_JOBS_URL)
            time.sleep(3)

            # Extract and save cookies
            cookies = extract_cookies(tab)

            if not cookies:
                logger.error("No cookies captured. Login may have failed.")
                return False

            logger.info(f"Captured {len(cookies)} cookies")

            # Save cookies
            cookie_manager = get_cookie_manager()
            if cookie_manager.save_cookies(cookies):
                logger.info("")
                logger.info("=" * 60)
                logger.info("SUCCESS! LinkedIn cookies saved.")
                logger.info("You can now run job searches with authenticated access.")
                logger.info("=" * 60)
                return True
            else:
                logger.error("Failed to save cookies")
                return False
        else:
            logger.error("Login was not completed in time")
            return False

    except Exception as e:
        logger.error(f"Login failed with error: {e}")
        return False
    finally:
        if browser:
            try:
                logger.info("Closing browser...")
                browser.quit()
            except:
                pass


def check_cookie_status():
    """Check and display saved cookie status."""
    cookie_manager = get_cookie_manager()

    if not cookie_manager.has_cookies():
        print("\nNo LinkedIn cookies saved.")
        print("Run 'python -m job_sources.linkedin_login' to log in.")
        return

    info = cookie_manager.get_cookie_info()
    if info:
        print("\n" + "=" * 60)
        print("LinkedIn Cookie Status")
        print("=" * 60)
        print(f"  Saved at:     {info.get('saved_at', 'Unknown')}")
        print(f"  Cookie count: {info.get('cookie_count', 0)}")
        print(f"  Domain:       {info.get('domain', 'Unknown')}")
        print("=" * 60)
    else:
        print("\nCould not read cookie information.")


def clear_cookies():
    """Clear saved LinkedIn cookies."""
    cookie_manager = get_cookie_manager()

    if not cookie_manager.has_cookies():
        print("\nNo cookies to clear.")
        return

    if cookie_manager.delete_cookies():
        print("\nLinkedIn cookies cleared successfully.")
    else:
        print("\nFailed to clear cookies.")


def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn Login Utility for authenticated scraping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m job_sources.linkedin_login          # Open browser for login
  python -m job_sources.linkedin_login --check  # Check cookie status
  python -m job_sources.linkedin_login --clear  # Clear saved cookies
        """
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check saved cookie status"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear saved cookies"
    )

    args = parser.parse_args()

    if args.check:
        check_cookie_status()
    elif args.clear:
        clear_cookies()
    else:
        success = interactive_login()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
