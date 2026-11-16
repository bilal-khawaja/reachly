"""Field validation shared by the API. Postgres CHECK constraints (migration 0003) use the same patterns."""
import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# optional http(s)://, domain with TLD, optional port and path/query
WEBSITE_RE = re.compile(r"^(https?://)?([A-Za-z0-9-]+\.)+[A-Za-z]{2,}(:[0-9]+)?(/[^\s]*)?$")

EMAIL_PG = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$"
WEBSITE_PG = r"^(https?://)?([A-Za-z0-9-]+\.)+[A-Za-z]{2,}(:[0-9]+)?(/[^[:space:]]*)?$"


def clean_email(v):
    """None / blank -> None. Otherwise must match EMAIL_RE; stored lowercase."""
    if v is None or not str(v).strip():
        return None
    v = str(v).strip()
    if len(v) > 254 or not EMAIL_RE.match(v):
        raise ValueError("invalid email address")
    return v.lower()


def clean_website(v):
    """None / blank -> None. Otherwise must match WEBSITE_RE."""
    if v is None or not str(v).strip():
        return None
    v = str(v).strip()
    if len(v) > 2048 or not WEBSITE_RE.match(v):
        raise ValueError("invalid website (e.g. example.com or https://example.com/page)")
    return v


def clean_phone(v):
    """Required: non-blank after trimming, max 40 chars."""
    if v is None or not str(v).strip():
        raise ValueError("phone is required")
    v = str(v).strip()
    if len(v) > 40:
        raise ValueError("phone is too long")
    return v
