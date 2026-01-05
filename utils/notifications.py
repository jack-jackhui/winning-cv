# utils/notifications.py

import os
import requests
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from config.settings import Config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# USER NOTIFICATION PREFERENCES (for per-user notifications)
# ──────────────────────────────────────────────────────────

class UserNotificationPrefs:
    """User notification preferences structure"""
    def __init__(
        self,
        user_email: str,
        email_alerts: bool = True,
        telegram_alerts: bool = False,
        wechat_alerts: bool = False,
        weekly_digest: bool = True,
        telegram_chat_id: Optional[str] = None,
        wechat_openid: Optional[str] = None,
        notification_email: Optional[str] = None
    ):
        self.user_email = user_email
        self.email_alerts = email_alerts
        self.telegram_alerts = telegram_alerts
        self.wechat_alerts = wechat_alerts
        self.weekly_digest = weekly_digest
        self.telegram_chat_id = telegram_chat_id
        self.wechat_openid = wechat_openid
        self.notification_email = notification_email or user_email

    def to_dict(self) -> dict:
        return {
            "user_email": self.user_email,
            "email_alerts": self.email_alerts,
            "telegram_alerts": self.telegram_alerts,
            "wechat_alerts": self.wechat_alerts,
            "weekly_digest": self.weekly_digest,
            "telegram_chat_id": self.telegram_chat_id,
            "wechat_openid": self.wechat_openid,
            "notification_email": self.notification_email,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserNotificationPrefs":
        return cls(
            user_email=data.get("user_email", ""),
            email_alerts=data.get("email_alerts", True),
            telegram_alerts=data.get("telegram_alerts", False),
            wechat_alerts=data.get("wechat_alerts", False),
            weekly_digest=data.get("weekly_digest", True),
            telegram_chat_id=data.get("telegram_chat_id"),
            wechat_openid=data.get("wechat_openid"),
            notification_email=data.get("notification_email"),
        )

def send_telegram_message(message: str):
    """
    Send a message to a Telegram chat using a bot token and chat id from environment variables.
    """
    TELEGRAM_BOT_TOKEN = Config.TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID = Config.TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram bot token or chat id not set in environment variables.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, data=data)
        if resp.status_code != 200:
            logger.warning(f"Telegram API error: {resp.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")

def send_email_notification(subject: str, body: str, to_email: Optional[str] = None):
    """
    Send an email notification. Requires SMTP settings in environment variables.

    Args:
        subject: Email subject
        body: Email body text
        to_email: Optional recipient email (defaults to DEFAULT_TO_EMAIL)
    """
    SMTP_HOST = Config.SMTP_SERVER
    SMTP_PORT = 465
    SMTP_USERNAME = Config.EMAIL_USER
    SMTP_PASSWORD = Config.EMAIL_PASSWORD
    EMAIL_FROM = Config.DEFAULT_FROM_EMAIL
    EMAIL_TO = to_email or Config.DEFAULT_TO_EMAIL

    if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logger.warning("Missing one or more SMTP or email settings in environment variables.")
        return False

    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO.split(','), msg.as_string())
        logger.info(f"Email notification sent to {EMAIL_TO}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")
        return False


def send_wechat_message(message: str, wechat_openid: Optional[str] = None) -> bool:
    """
    Send a message via WeChat Work (企业微信) webhook or WeCom API.

    Supports two modes:
    1. Webhook mode: Uses WECHAT_BOT_URL for group bot notifications
    2. OpenID mode: Direct user notification (requires additional API setup)

    Args:
        message: The message to send
        wechat_openid: Optional user's WeChat OpenID for direct messaging

    Returns:
        True if sent successfully, False otherwise
    """
    WECHAT_BOT_URL = Config.WECHAT_BOT_URL
    WECHAT_API_KEY = Config.WECHAT_API_KEY

    # Mode 1: Webhook bot (group notifications)
    if WECHAT_BOT_URL:
        try:
            # WeChat Work webhook format
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": message
                }
            }

            resp = requests.post(WECHAT_BOT_URL, json=payload, timeout=10)

            if resp.status_code == 200:
                result = resp.json()
                if result.get("errcode") == 0:
                    logger.info("WeChat webhook message sent successfully")
                    return True
                else:
                    logger.warning(f"WeChat webhook error: {result.get('errmsg')}")
                    return False
            else:
                logger.warning(f"WeChat webhook HTTP error: {resp.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to send WeChat webhook message: {str(e)}")
            return False

    # Mode 2: Direct user notification via WeCom API (if openid provided)
    elif wechat_openid and WECHAT_API_KEY:
        try:
            # This would require WeCom Corp API integration
            # For now, log that direct messaging is not fully implemented
            logger.warning("WeChat direct messaging requires WeCom Corp API setup")
            return False

        except Exception as e:
            logger.error(f"Failed to send WeChat direct message: {str(e)}")
            return False

    else:
        logger.warning("WeChat not configured: Missing WECHAT_BOT_URL or WECHAT_API_KEY")
        return False


def send_telegram_to_user(message: str, chat_id: str) -> bool:
    """
    Send a Telegram message to a specific chat ID (for per-user notifications).

    Args:
        message: The message to send
        chat_id: User's Telegram chat ID

    Returns:
        True if sent successfully, False otherwise
    """
    TELEGRAM_BOT_TOKEN = Config.TELEGRAM_BOT_TOKEN

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not configured")
        return False

    if not chat_id:
        logger.warning("No Telegram chat ID provided")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("ok"):
                logger.info(f"Telegram message sent to chat {chat_id}")
                return True
            else:
                logger.warning(f"Telegram API error: {result.get('description')}")
                return False
        else:
            logger.warning(f"Telegram API HTTP error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")
        return False

def notify_all(job_count: int, job_titles: list, airtable_link: str):
    """
    Send both Telegram and Email notifications about job updates.
    """
    def format_job(job):
        title = job.get('Job Title', 'N/A')
        company = job.get('Company', 'N/A')
        link = job.get('Job Link', '')
        cv = job.get('CV URL', '')
        score = job.get('Score', '')
        return (
            f"*{title}*\n"
            f"*{company}*\n"
            f"🔗 [Job Link]({link})\n"
            f"📄 [CV]({cv})\n"
            f"⭐ Score: {score}"
        )

    def format_job_email(job):
        title = job.get('Job Title', 'N/A')
        company = job.get('Company', 'N/A')
        link = job.get('Job Link', '')
        cv = job.get('CV URL', '')
        score = job.get('Score', '')
        return (
            f"{title}\n"
            f"*{company}*\n"
            f"  Job Link: {link}\n"
            f"  CV: {cv}\n"
            f"  Score: {score}"
        )

    jobs_list = "\n\n".join([format_job(job) for job in job_titles])
    jobs_list_email = "\n\n".join([format_job_email(job) for job in job_titles])

    message = (
        f"📝 **Today's WinningCV Matching Jobs Update!🎉**\n"
        f"*Jobs matching*: {job_count}\n\n"
        f"{jobs_list}\n\n"
        f"Check the details in : {airtable_link}"
    )

    # Telegram (global - uses default chat ID)
    send_telegram_message(message)

    # Email (plain text)
    subject = f"WinningCV Update: {job_count} Matching Jobs"
    body = (
        f"Hi,\n\n"
        f"There are {job_count} jobs matching your criteria.\n\n"
        f"Job titles:\n{jobs_list_email}\n\n"
        f"Check the latest in Airtable: {airtable_link}\n\n"
        f"- From WinningCV Team"
    )
    send_email_notification(subject, body)


def notify_user(
    user_prefs: UserNotificationPrefs,
    job_count: int,
    job_titles: List[Dict[str, Any]],
    airtable_link: str
) -> Dict[str, bool]:
    """
    Send notifications to a specific user based on their preferences.

    Args:
        user_prefs: User's notification preferences
        job_count: Number of matching jobs
        job_titles: List of job dictionaries with job details
        airtable_link: Link to Airtable view

    Returns:
        Dictionary with status of each notification channel
    """
    results = {
        "email": False,
        "telegram": False,
        "wechat": False
    }

    # Format messages
    def format_job_markdown(job):
        title = job.get('Job Title', 'N/A')
        company = job.get('Company', 'N/A')
        link = job.get('Job Link', '')
        cv = job.get('CV URL', '')
        score = job.get('Score', '')
        return (
            f"**{title}**\n"
            f"*{company}*\n"
            f"🔗 [Job Link]({link})\n"
            f"📄 [CV]({cv})\n"
            f"⭐ Score: {score}"
        )

    def format_job_plain(job):
        title = job.get('Job Title', 'N/A')
        company = job.get('Company', 'N/A')
        link = job.get('Job Link', '')
        cv = job.get('CV URL', '')
        score = job.get('Score', '')
        return (
            f"{title}\n"
            f"  Company: {company}\n"
            f"  Job Link: {link}\n"
            f"  CV: {cv}\n"
            f"  Score: {score}"
        )

    jobs_markdown = "\n\n".join([format_job_markdown(job) for job in job_titles])
    jobs_plain = "\n\n".join([format_job_plain(job) for job in job_titles])

    # Email notification
    if user_prefs.email_alerts and user_prefs.notification_email:
        subject = f"WinningCV: {job_count} New Matching Jobs Found!"
        body = (
            f"Hi,\n\n"
            f"Great news! We found {job_count} jobs matching your criteria.\n\n"
            f"Here are your matches:\n\n{jobs_plain}\n\n"
            f"View all matches: {airtable_link}\n\n"
            f"Best of luck with your applications!\n"
            f"- The WinningCV Team\n\n"
            f"---\n"
            f"To manage your notification preferences, visit your profile settings."
        )
        results["email"] = send_email_notification(subject, body, user_prefs.notification_email)

    # Telegram notification
    if user_prefs.telegram_alerts and user_prefs.telegram_chat_id:
        message = (
            f"📝 **WinningCV Job Alert!** 🎉\n\n"
            f"*{job_count} new matching jobs found!*\n\n"
            f"{jobs_markdown}\n\n"
            f"[View all matches]({airtable_link})"
        )
        results["telegram"] = send_telegram_to_user(message, user_prefs.telegram_chat_id)

    # WeChat notification
    if user_prefs.wechat_alerts:
        message = (
            f"📝 **WinningCV Job Alert!** 🎉\n\n"
            f"**{job_count} new matching jobs found!**\n\n"
            f"{jobs_markdown}\n\n"
            f"[View all matches]({airtable_link})"
        )
        results["wechat"] = send_wechat_message(message, user_prefs.wechat_openid)

    logger.info(f"Notification results for {user_prefs.user_email}: {results}")
    return results


def notify_all_users(
    job_count: int,
    job_titles: List[Dict[str, Any]],
    airtable_link: str,
    airtable_manager=None
) -> Dict[str, Dict[str, bool]]:
    """
    Send notifications to all users who have notifications enabled.

    This function queries the Airtable to get all users with at least one
    notification channel enabled and sends them notifications.

    Args:
        job_count: Number of matching jobs
        job_titles: List of job dictionaries with job details
        airtable_link: Link to Airtable view
        airtable_manager: Optional AirtableManager instance. If not provided,
                         will create one using default config.

    Returns:
        Dictionary mapping user emails to their notification results
    """
    from data_store.airtable_manager import AirtableManager
    from config.settings import Config

    # Create manager if not provided
    if airtable_manager is None:
        airtable_manager = AirtableManager(
            api_key=Config.AIRTABLE_API_KEY,
            base_id=Config.AIRTABLE_BASE_ID,
            table_id=Config.AIRTABLE_TABLE_ID
        )

    # Get all users with notifications enabled
    users = airtable_manager.get_users_with_notifications_enabled()

    if not users:
        logger.info("No users with notifications enabled found")
        return {}

    results = {}

    for user_data in users:
        user_email = user_data.get("user_email")
        if not user_email:
            continue

        # Create user preferences from stored data
        user_prefs = UserNotificationPrefs(
            user_email=user_email,
            email_alerts=user_data.get("email_alerts", True),
            telegram_alerts=user_data.get("telegram_alerts", False),
            wechat_alerts=user_data.get("wechat_alerts", False),
            weekly_digest=user_data.get("weekly_digest", True),
            telegram_chat_id=user_data.get("telegram_chat_id"),
            wechat_openid=user_data.get("wechat_openid"),
            notification_email=user_data.get("notification_email")
        )

        try:
            user_results = notify_user(user_prefs, job_count, job_titles, airtable_link)
            results[user_email] = user_results
        except Exception as e:
            logger.error(f"Failed to send notifications to {user_email}: {str(e)}")
            results[user_email] = {"error": str(e)}

    logger.info(f"Sent notifications to {len(results)} users")
    return results


def notify_specific_user(
    user_email: str,
    job_count: int,
    job_titles: List[Dict[str, Any]],
    airtable_link: str,
    airtable_manager=None
) -> Dict[str, bool]:
    """
    Send notifications to a specific user based on their stored preferences.

    Args:
        user_email: The user's email address
        job_count: Number of matching jobs
        job_titles: List of job dictionaries with job details
        airtable_link: Link to Airtable view
        airtable_manager: Optional AirtableManager instance

    Returns:
        Dictionary with status of each notification channel
    """
    from data_store.airtable_manager import AirtableManager
    from config.settings import Config

    # Create manager if not provided
    if airtable_manager is None:
        airtable_manager = AirtableManager(
            api_key=Config.AIRTABLE_API_KEY,
            base_id=Config.AIRTABLE_BASE_ID,
            table_id=Config.AIRTABLE_TABLE_ID
        )

    # Get user's notification preferences
    prefs_data = airtable_manager.get_notification_preferences(user_email)

    if not prefs_data:
        logger.info(f"No notification preferences found for {user_email}, using defaults")
        prefs_data = {
            "email_alerts": True,
            "telegram_alerts": False,
            "wechat_alerts": False,
            "weekly_digest": True,
        }

    # Create user preferences object
    user_prefs = UserNotificationPrefs(
        user_email=user_email,
        email_alerts=prefs_data.get("email_alerts", True),
        telegram_alerts=prefs_data.get("telegram_alerts", False),
        wechat_alerts=prefs_data.get("wechat_alerts", False),
        weekly_digest=prefs_data.get("weekly_digest", True),
        telegram_chat_id=prefs_data.get("telegram_chat_id"),
        wechat_openid=prefs_data.get("wechat_openid"),
        notification_email=prefs_data.get("notification_email")
    )

    return notify_user(user_prefs, job_count, job_titles, airtable_link)