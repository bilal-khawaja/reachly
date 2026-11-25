"""Tiny in-memory limiter for failed logins (per IP). Fine for one process; use Redis if you scale to many."""
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

MAX_FAILURES = 5
WINDOW_SECONDS = 300

_lock = threading.Lock()
_failures: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    if os.getenv("TRUST_PROXY", "false").lower() in ("1", "true", "yes"):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _recent(ip: str, now: float) -> deque:
    q = _failures[ip]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    return q


def check(ip: str) -> None:
    now = time.monotonic()
    with _lock:
        q = _recent(ip, now)
        if len(q) >= MAX_FAILURES:
            retry = int(WINDOW_SECONDS - (now - q[0])) + 1
            raise HTTPException(429, "Too many failed attempts. Try again later.", headers={"Retry-After": str(retry)})


def record_failure(ip: str) -> None:
    with _lock:
        _recent(ip, time.monotonic()).append(time.monotonic())


def reset(ip: str | None = None) -> None:
    with _lock:
        _failures.pop(ip, None) if ip else _failures.clear()
