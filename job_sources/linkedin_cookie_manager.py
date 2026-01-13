"""
LinkedIn Cookie Manager for authenticated scraping.

This module provides cookie-based authentication for LinkedIn scraping:
1. Save browser cookies after manual login
2. Load cookies for subsequent headless scraping
3. Validate if stored cookies are still valid

Pattern inspired by xiaohongshu-mcp for persistent session management.
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Default cookie storage location
DEFAULT_COOKIE_DIR = Path(__file__).parent.parent / "cookies"
LINKEDIN_COOKIE_FILE = "linkedin_cookies.json"


class LinkedInCookieManager:
    """Manages LinkedIn session cookies for authenticated scraping."""

    def __init__(self, cookie_dir: Optional[str] = None):
        """
        Initialize the cookie manager.

        Args:
            cookie_dir: Directory to store cookies. Defaults to project's cookies/ folder.
        """
        self.cookie_dir = Path(cookie_dir) if cookie_dir else DEFAULT_COOKIE_DIR
        self.cookie_file = self.cookie_dir / LINKEDIN_COOKIE_FILE
        self._ensure_cookie_dir()

    def _ensure_cookie_dir(self):
        """Create cookie directory if it doesn't exist."""
        try:
            self.cookie_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass  # Directory might exist but be read-only (mounted volume)

        # Add .gitignore to prevent committing cookies (optional, ignore errors)
        gitignore = self.cookie_dir / ".gitignore"
        if not gitignore.exists():
            try:
                gitignore.write_text("*\n!.gitignore\n")
            except PermissionError:
                pass  # Read-only mount, skip gitignore creation

    def save_cookies(self, cookies: List[Dict]) -> bool:
        """
        Save cookies to file.

        Args:
            cookies: List of cookie dictionaries from browser.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            cookie_data = {
                "cookies": cookies,
                "saved_at": datetime.now().isoformat(),
                "domain": "linkedin.com"
            }
            with open(self.cookie_file, "w") as f:
                json.dump(cookie_data, f, indent=2)
            logger.info(f"Saved {len(cookies)} LinkedIn cookies to {self.cookie_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False

    def load_cookies(self) -> Optional[List[Dict]]:
        """
        Load cookies from file.

        Returns:
            List of cookie dictionaries, or None if not found/invalid.
        """
        if not self.cookie_file.exists():
            logger.warning(f"No saved cookies found at {self.cookie_file}")
            return None

        try:
            with open(self.cookie_file, "r") as f:
                cookie_data = json.load(f)

            cookies = cookie_data.get("cookies", [])
            saved_at = cookie_data.get("saved_at", "unknown")
            logger.info(f"Loaded {len(cookies)} LinkedIn cookies (saved at {saved_at})")
            return cookies
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return None

    def has_cookies(self) -> bool:
        """Check if saved cookies exist."""
        return self.cookie_file.exists()

    def delete_cookies(self) -> bool:
        """Delete saved cookies."""
        try:
            if self.cookie_file.exists():
                self.cookie_file.unlink()
                logger.info("Deleted LinkedIn cookies")
            return True
        except Exception as e:
            logger.error(f"Failed to delete cookies: {e}")
            return False

    def get_cookie_info(self) -> Optional[Dict]:
        """Get information about stored cookies without loading them fully."""
        if not self.cookie_file.exists():
            return None

        try:
            with open(self.cookie_file, "r") as f:
                cookie_data = json.load(f)
            return {
                "saved_at": cookie_data.get("saved_at"),
                "cookie_count": len(cookie_data.get("cookies", [])),
                "domain": cookie_data.get("domain")
            }
        except Exception as e:
            logger.error(f"Failed to get cookie info: {e}")
            return None


def get_cookie_manager(cookie_dir: Optional[str] = None) -> LinkedInCookieManager:
    """Factory function to get a cookie manager instance."""
    return LinkedInCookieManager(cookie_dir)
