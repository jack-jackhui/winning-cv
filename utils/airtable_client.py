"""
Robust Airtable client configuration with timeouts, retries, and connection management.

This module provides a properly configured pyairtable Api instance that:
- Sets connection and read timeouts to prevent hanging requests
- Implements exponential backoff retry for transient failures
- Handles rate limits (429) and server errors (5xx) gracefully
"""
import logging
from typing import Optional, Tuple
from urllib3.util import Retry
from pyairtable import Api

from config.settings import Config

logger = logging.getLogger(__name__)

# Connection configuration
DEFAULT_CONNECT_TIMEOUT = 10  # seconds to establish connection
DEFAULT_READ_TIMEOUT = 30  # seconds to wait for response
DEFAULT_RETRY_TOTAL = 3  # total retry attempts
DEFAULT_BACKOFF_FACTOR = 1.0  # exponential backoff: 1s, 2s, 4s...

# HTTP status codes to retry on
RETRY_STATUS_CODES = [
    408,  # Request Timeout
    429,  # Too Many Requests (rate limit)
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
]


def create_retry_strategy(
    total: int = DEFAULT_RETRY_TOTAL,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    status_forcelist: Optional[list] = None,
) -> Retry:
    """
    Create a urllib3 Retry strategy for Airtable API calls.

    Args:
        total: Maximum number of retries
        backoff_factor: Factor for exponential backoff between retries
        status_forcelist: HTTP status codes that trigger a retry

    Returns:
        Configured Retry instance
    """
    if status_forcelist is None:
        status_forcelist = RETRY_STATUS_CODES

    return Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        raise_on_status=False,  # Let pyairtable handle error responses
    )


def create_airtable_api(
    api_key: Optional[str] = None,
    timeout: Optional[Tuple[int, int]] = None,
    retry_strategy: Optional[Retry] = None,
) -> Api:
    """
    Create a robustly configured pyairtable Api instance.

    Args:
        api_key: Airtable API key (defaults to Config.AIRTABLE_API_KEY)
        timeout: Tuple of (connect_timeout, read_timeout) in seconds
        retry_strategy: Custom retry strategy (defaults to create_retry_strategy())

    Returns:
        Configured Api instance with timeout and retry handling
    """
    if api_key is None:
        api_key = Config.AIRTABLE_API_KEY

    if timeout is None:
        timeout = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT)

    if retry_strategy is None:
        retry_strategy = create_retry_strategy()

    logger.debug(
        "Creating Airtable API client with timeout=%s, retry_total=%s",
        timeout,
        retry_strategy.total if retry_strategy else "none"
    )

    return Api(
        api_key,
        timeout=timeout,
        retry_strategy=retry_strategy,
    )


# Global singleton for shared usage
_airtable_api: Optional[Api] = None


def get_airtable_api() -> Api:
    """
    Get or create the global Airtable API instance.

    This provides a shared, properly configured Api instance for the application.
    The singleton pattern ensures consistent configuration across all Airtable
    operations while allowing connection pooling to work efficiently.

    Returns:
        Configured Api instance
    """
    global _airtable_api
    if _airtable_api is None:
        _airtable_api = create_airtable_api()
        logger.info("Initialized global Airtable API client with robust connection settings")
    return _airtable_api


def reset_airtable_api() -> None:
    """
    Reset the global Airtable API instance.

    Use this to force recreation of the API client, which can help
    recover from connection pool issues.
    """
    global _airtable_api
    if _airtable_api is not None:
        logger.info("Resetting global Airtable API client")
        _airtable_api = None
