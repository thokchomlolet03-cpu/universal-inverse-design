"""Shared HTTP retry utility with exponential backoff.

Centralizes retry logic for all API clients (PubMed, UniProt, KEGG, ChEMBL,
Gemini) instead of duplicating try/except blocks with no retry across 4+ modules.

Usage:
    from uid_engine.utils.retry import retry_request
    response = retry_request("GET", "https://api.example.com/data", params={...})
"""

import time
from typing import Optional

import requests
from rich.console import Console

console = Console()

# Default retry configuration
MAX_RETRIES = 3
BACKOFF_BASE = 2.0  # seconds — delays will be 2, 4, 8
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def retry_request(
    method: str,
    url: str,
    max_retries: int = MAX_RETRIES,
    backoff_base: float = BACKOFF_BASE,
    timeout: int = 30,
    **kwargs,
) -> requests.Response:
    """Make an HTTP request with exponential backoff on transient failures.

    Args:
        method: HTTP method ("GET", "POST", etc.).
        url: The target URL.
        max_retries: Maximum number of retry attempts.
        backoff_base: Base for exponential delay (delay = base ** attempt).
        timeout: Request timeout in seconds.
        **kwargs: Additional arguments passed to requests.request().

    Returns:
        The successful Response object.

    Raises:
        requests.exceptions.RequestException: If all retries are exhausted.
    """
    kwargs.setdefault("timeout", timeout)
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            response = requests.request(method, url, **kwargs)

            # If we get a retryable status code, treat it like a transient error
            if response.status_code in RETRYABLE_STATUS_CODES:
                wait = backoff_base ** attempt
                console.print(
                    f"[yellow]⚠ {response.status_code} from {url} — "
                    f"retrying in {wait:.1f}s (attempt {attempt + 1}/{max_retries + 1})[/yellow]"
                )
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.ConnectionError as e:
            last_exception = e
            wait = backoff_base ** attempt
            console.print(
                f"[yellow]⚠ Connection error for {url} — "
                f"retrying in {wait:.1f}s (attempt {attempt + 1}/{max_retries + 1})[/yellow]"
            )
            time.sleep(wait)

        except requests.exceptions.Timeout as e:
            last_exception = e
            wait = backoff_base ** attempt
            console.print(
                f"[yellow]⚠ Timeout for {url} — "
                f"retrying in {wait:.1f}s (attempt {attempt + 1}/{max_retries + 1})[/yellow]"
            )
            time.sleep(wait)

        except requests.exceptions.RequestException as e:
            # Non-retryable error (4xx other than 429) — fail immediately
            raise

    # All retries exhausted
    raise requests.exceptions.RetryError(
        f"All {max_retries + 1} attempts failed for {url}",
        response=None,  # type: ignore[arg-type]
    ) from last_exception
