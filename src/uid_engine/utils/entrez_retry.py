"""NCBI Entrez retry wrapper — rate-limited Biopython fetch with backoff.

NCBI E-utilities enforces strict rate limits:
  - Without API key: 3 requests/second max
  - With NCBI_API_KEY set: 10 requests/second max

A failed Entrez.efetch batch silently drops that batch of papers with
no retry. This wrapper enforces the rate limit AND retries on transient
failures (network blips, NCBI 429, temporary server errors).

Usage:
    from uid_engine.utils.entrez_retry import entrez_fetch

    records = entrez_fetch(db="pubmed", id="12345,67890", rettype="xml")
"""

import time
from typing import Any, Optional

from Bio import Entrez
from rich.console import Console

console = Console()

# NCBI rate limits (requests per second)
_RATE_LIMIT_NO_KEY = 0.34      # ~3 req/sec
_RATE_LIMIT_WITH_KEY = 0.10    # ~10 req/sec

# Retry config
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0             # delays: 2s, 4s, 8s


def entrez_fetch(
    db: str,
    rettype: str = "xml",
    retmode: str = "xml",
    max_retries: int = _MAX_RETRIES,
    use_api_key: bool = True,
    **kwargs: Any,
) -> Optional[Any]:
    """Fetch from NCBI Entrez with rate limiting and exponential backoff.

    Automatically applies the correct per-request delay based on whether
    an NCBI API key is configured. Retries up to max_retries times on
    network errors and NCBI 429/500 responses.

    Args:
        db: NCBI database name (e.g., "pubmed", "protein").
        rettype: Return type (e.g., "xml", "fasta").
        retmode: Return mode (e.g., "xml", "text").
        max_retries: Maximum retry attempts before raising.
        use_api_key: Whether to apply API-key rate limit (faster).
        **kwargs: Additional keyword arguments passed to Entrez.efetch().

    Returns:
        Parsed Entrez record, or None if all retries fail.
    """
    from uid_engine import config  # deferred to avoid circular import

    # Determine correct inter-request delay
    has_key = bool(getattr(config, "NCBI_API_KEY", None))
    delay = _RATE_LIMIT_WITH_KEY if (use_api_key and has_key) else _RATE_LIMIT_NO_KEY

    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            handle = Entrez.efetch(db=db, rettype=rettype, retmode=retmode, **kwargs)
            record = Entrez.read(handle)
            handle.close()

            # Respect rate limit after each successful fetch
            time.sleep(delay)
            return record

        except Exception as e:
            last_exc = e
            wait = _BACKOFF_BASE ** attempt
            console.print(
                f"[yellow]⚠ Entrez.efetch failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"{type(e).__name__}: {e} — retrying in {wait:.0f}s[/yellow]"
            )
            time.sleep(wait)

    console.print(
        f"[red]✗ Entrez.efetch exhausted {max_retries + 1} retries. "
        f"Last error: {last_exc}[/red]"
    )
    return None


def entrez_search(
    db: str,
    term: str,
    max_retries: int = _MAX_RETRIES,
    **kwargs: Any,
) -> Optional[Any]:
    """Search NCBI Entrez with rate limiting and exponential backoff.

    Args:
        db: NCBI database name.
        term: Search query string.
        max_retries: Maximum retry attempts.
        **kwargs: Additional arguments for Entrez.esearch().

    Returns:
        Parsed search record, or None if all retries fail.
    """
    from uid_engine import config

    has_key = bool(getattr(config, "NCBI_API_KEY", None))
    delay = _RATE_LIMIT_WITH_KEY if has_key else _RATE_LIMIT_NO_KEY

    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            handle = Entrez.esearch(db=db, term=term, **kwargs)
            record = Entrez.read(handle)
            handle.close()
            time.sleep(delay)
            return record

        except Exception as e:
            last_exc = e
            wait = _BACKOFF_BASE ** attempt
            console.print(
                f"[yellow]⚠ Entrez.esearch failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"{type(e).__name__}: {e} — retrying in {wait:.0f}s[/yellow]"
            )
            time.sleep(wait)

    console.print(
        f"[red]✗ Entrez.esearch exhausted {max_retries + 1} retries. "
        f"Last error: {last_exc}[/red]"
    )
    return None
