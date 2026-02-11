"""
Lightweight in-memory TTL cache for the SkyLark BI Agent.

Thread-safe dictionary-based cache with automatic expiry.
Drop-in replaceable with Redis by swapping this module.
"""

import hashlib
import logging
import re
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Thread-safe in-memory cache with per-key TTL.

    Each entry stores (value, expires_at).  Expired entries are lazily
    evicted on access and periodically purged via ``purge_expired()``.
    """

    def __init__(self, default_ttl: int = 180):
        """
        Args:
            default_ttl: Default time-to-live in seconds (used when
                         ``ttl`` is not passed to ``set``).
        """
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    # ------------------------------------------------------------------
    #  Core API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or ``None`` if missing / expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                logger.debug(f"Cache expired: {key}")
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store *value* under *key* with an optional custom TTL (seconds)."""
        ttl = ttl if ttl is not None else self.default_ttl
        with self._lock:
            self._store[key] = (value, time.time() + ttl)
        logger.debug(f"Cache set: {key} (ttl={ttl}s)")

    def delete(self, key: str) -> bool:
        """Remove a single key.  Returns ``True`` if it existed."""
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> int:
        """Drop all entries.  Returns the count of removed keys."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
        logger.info(f"Cache cleared ({count} entries)")
        return count

    def purge_expired(self) -> int:
        """Remove all expired entries.  Returns count purged."""
        now = time.time()
        with self._lock:
            expired = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired:
                del self._store[k]
        if expired:
            logger.debug(f"Purged {len(expired)} expired cache entries")
        return len(expired)

    # ------------------------------------------------------------------
    #  Introspection helpers
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return cache statistics (for /health or debugging)."""
        now = time.time()
        with self._lock:
            total = len(self._store)
            alive = sum(1 for _, (_, exp) in self._store.items() if now <= exp)
        return {"total_entries": total, "alive": alive, "expired": total - alive}

    def has(self, key: str) -> bool:
        """Check if a non-expired key exists without returning its value."""
        return self.get(key) is not None


# ======================================================================
#  Global cache singletons
# ======================================================================

# Board data changes infrequently — cache for 3 minutes (180 s).
board_cache = TTLCache(default_ttl=180)

# AI (Groq) responses are deterministic for identical questions —
# cache for 5 minutes (300 s).
response_cache = TTLCache(default_ttl=300)


# ------------------------------------------------------------------
#  Key-building helpers
# ------------------------------------------------------------------

_STRIP_RE = re.compile(r"[^a-z0-9 ]+")


def normalize_question(question: str) -> str:
    """
    Produce a stable cache key from a user question.

    Lowercases, strips punctuation and collapses whitespace so that
    ``"What's our pipeline?"`` and ``"whats our pipeline"`` hit the
    same cache entry.
    """
    q = question.lower().strip()
    q = _STRIP_RE.sub("", q)
    q = " ".join(q.split())
    return q


def make_response_key(question: str) -> str:
    """SHA-256 based cache key for a normalised question."""
    norm = normalize_question(question)
    digest = hashlib.sha256(norm.encode()).hexdigest()[:16]
    return f"resp:{digest}"


BOARD_DATA_KEY = "boards:all"
