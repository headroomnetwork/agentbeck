"""In-memory sliding-window rate limiter.

Fine for a single-instance deployment. Replace with Redis or similar
if Agent Beck ever runs across multiple processes.
"""
import time
from collections import defaultdict
from typing import Dict, List, Tuple

# (client_ip, limit_key) -> [(timestamp, method, path), ...]
_requests: Dict[Tuple[str, Tuple[str, str]], List[Tuple[float, str, str]]] = defaultdict(list)

# Limits: limit_key -> (window_seconds, max_requests)
LIMITS = {
    ("POST", "/reports"): (60, 10),
    ("POST", "/reports/{id}/worked"): (60, 20),
    ("DELETE", "/reports/{id}"): (60, 10),
    ("PATCH", "/reports/{id}"): (60, 10),
    ("GET", "default"): (60, 60),
    ("default", "default"): (60, 60),
}


def is_limited(client_ip: str, method: str, path: str) -> Tuple[bool, float]:
    """Return (is_limited, retry_after_seconds)."""
    now = time.time()
    limit_key = _get_limit_key(method, path)
    window_sec, max_req = LIMITS[limit_key]

    # Prune old entries for this bucket
    cutoff = now - window_sec
    bucket = _requests[(client_ip, limit_key)]
    bucket[:] = [entry for entry in bucket if entry[0] > cutoff]

    if len(bucket) >= max_req:
        oldest_in_window = bucket[0][0] if bucket else now
        retry_after = window_sec - (now - oldest_in_window)
        return True, max(retry_after, 1.0)

    # Record this request
    bucket.append((now, method, path))
    return False, 0.0


def reset():
    """Clear all rate-limit state. Use in tests between runs."""
    _requests.clear()


def _get_limit_key(method: str, path: str) -> Tuple[str, str]:
    exact = (method, path)
    if exact in LIMITS:
        return exact
    if method == "POST" and path.startswith("/reports/") and path.endswith("/worked"):
        return ("POST", "/reports/{id}/worked")
    if method in ("DELETE", "PATCH") and path.startswith("/reports/"):
        return (method, "/reports/{id}")
    # Any GET request
    if method == "GET":
        return ("GET", "default")
    return ("default", "default")
