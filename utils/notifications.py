# utils/notifications.py

import os
import requests
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import Config

logger = logging.getLogger(__name__)

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

def send_email_notification(subject: str, body: str):
    """
    Send an email notification. Requires SMTP settings in environment variables.
    """
    SMTP_HOST = Config.SMTP_SERVER
    SMTP_PORT = 465
    SMTP_USERNAME = Config.EMAIL_USER
    SMTP_PASSWORD = Config.EMAIL_PASSWORD
    EMAIL_FROM = Config.DEFAULT_FROM_EMAIL
    EMAIL_TO = Config.DEFAULT_TO_EMAIL
    if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO]):
        logger.warning("Missing one or more SMTP or email settings in environment variables.")
        return
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            # server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO.split(','), msg.as_string())
        logger.info("Email notification sent.")
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")

def notify_all(job_count: int, job_titles: list, airtable_link: str):
    """
    Send both Telegram and Email notifications about job updates.
    """
    jobs_list = "\n".join([f"- {title}" for title in job_titles])
    message = (
        f"📝 **Today's WinningCV Matching Jobs Update!🎉**\n"
        f"*Jobs matching*: {job_count}\n\n"
        f"{jobs_list}\n\n"
        f"Check the details in : {airtable_link}"
    )
    # Telegram (Markdown, so escape underscores if present)
    telegram_message = message.replace('_', '\\_')
    send_telegram_message(telegram_message)

    # Email (plain text)
    subject = f"WinningCV Update: {job_count} Matching Jobs"
    body = (
        f"Hi,\n\n"
        f"There are {job_count} jobs matching your criteria.\n\n"
        f"Job titles:\n{jobs_list}\n\n"
        f"Check the latest in Airtable: {airtable_link}\n\n"
        f"- From WinningCV Team"
    )
    send_email_notification(subject, body)