"""CSV / XLSX parsing for bulk lead import. Pure helpers: no DB, no FastAPI."""
import csv
import io
import re
from pathlib import Path

COLUMNS = [
    {"name": "name", "required": True, "example": "Acme Plumbing", "hint": "Business name"},
    {"name": "phone", "required": True, "example": "506-555-0100", "hint": "Max 40 chars. Keep as text so leading 0s survive"},
    {"name": "email", "required": False, "example": "info@acme.com", "hint": "Valid email or blank"},
    {"name": "website", "required": False, "example": "acme.com", "hint": "Domain or URL, or blank"},
    {"name": "business_type", "required": False, "example": "plumbing", "hint": "Free text, e.g. clinic, hvac"},
    {"name": "city", "required": False, "example": "Moncton", "hint": "Free text"},
    {"name": "country", "required": False, "example": "Canada", "hint": "Free text"},
    {"name": "channel", "required": False, "example": "phone", "hint": "phone, whatsapp, email, instagram, linkedin, facebook (default phone)"},
    {"name": "status", "required": False, "example": "new", "hint": "new, contacted, replied, meeting_scheduled, proposal_sent, won, lost (default new)"},
    {"name": "notes", "required": False, "example": "Called Mon, call back Fri", "hint": "Free text"},
]
ALLOWED = [c["name"] for c in COLUMNS]
REQUIRED = [c["name"] for c in COLUMNS if c["required"]]
CHANNELS = ["phone", "whatsapp", "email", "instagram", "linkedin", "facebook"]

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000
EXTENSIONS = {".csv", ".xlsx"}


class ImportFormatError(ValueError):
    """File-level problem (bad type, wrong/extra/missing columns). Whole file rejected."""


def norm_header(h) -> str:
    return re.sub(r"[\s\-]+", "_", str(h if h is not None else "").strip().lower())


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _read_csv(data: bytes) -> list[list[str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportFormatError("CSV must be UTF-8 encoded (in Excel: Save As > CSV UTF-8)")
    return [[_cell(c) for c in row] for row in csv.reader(io.StringIO(text))]


def _read_xlsx(data: bytes) -> list[list[str]]:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        raise ImportFormatError("Could not read this .xlsx file. Is it a valid, unprotected workbook?")
    try:
        ws = wb.worksheets[0]
        return [[_cell(c) for c in row] for row in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def read_table(filename: str, data: bytes) -> tuple[list[str], list[tuple[int, dict]]]:
    """Return (headers, [(sheet_row_number, {column: str})]) with the header strictly validated."""
    ext = Path(filename or "").suffix.lower()
    if ext not in EXTENSIONS:
        raise ImportFormatError("Only .csv and .xlsx files are supported")
    if len(data) > MAX_BYTES:
        raise ImportFormatError(f"File too large (max {MAX_BYTES // 1024 // 1024} MB)")
    grid = _read_csv(data) if ext == ".csv" else _read_xlsx(data)

    start = next((i for i, r in enumerate(grid) if any(r)), None)
    if start is None:
        raise ImportFormatError("File is empty")
    header = [norm_header(h) for h in grid[start]]
    body = grid[start + 1:]

    width = len(header)
    while width and not header[width - 1] and not any(len(r) >= width and r[width - 1] for r in body):
        width -= 1
    header = header[:width]
    if "" in header:
        raise ImportFormatError("A column has data but no header name. Remove it or name it")

    dupes = sorted({h for h in header if header.count(h) > 1})
    if dupes:
        raise ImportFormatError(f"Duplicate columns: {', '.join(dupes)}")
    unknown = [h for h in header if h not in ALLOWED]
    if unknown:
        raise ImportFormatError(
            f"Unknown column(s): {', '.join(unknown)}. Remove them. Allowed: {', '.join(ALLOWED)}"
        )
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        raise ImportFormatError(f"Missing required column(s): {', '.join(missing)}")

    rows = []
    for offset, r in enumerate(body, start=start + 2):
        r = (r + [""] * width)[:width]
        if not any(r):
            continue
        rows.append((offset, dict(zip(header, r))))
    if not rows:
        raise ImportFormatError("No data rows found under the header")
    if len(rows) > MAX_ROWS:
        raise ImportFormatError(f"Too many rows ({len(rows)}). Max {MAX_ROWS} per import")
    return header, rows


_PHONE_LIKE = re.compile(r"^[+-]?[\d\s().-]+$")


def _safe_cell(v) -> str:
    """Neutralise spreadsheet formula injection (=, @, +, -, tab, CR) while keeping real phone numbers intact."""
    s = "" if v is None else str(v)
    if s and (s[0] in "=@\t\r" or (s[0] in "+-" and not _PHONE_LIKE.match(s))):
        return "'" + s
    return s


def export_csv(rows: list[dict]) -> str:
    """Same columns as the import template, so an export can be re-imported."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(ALLOWED)
    for r in rows:
        w.writerow([_safe_cell(r.get(c)) for c in ALLOWED])
    return buf.getvalue()


def template_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(ALLOWED)
    w.writerow([c["example"] for c in COLUMNS])
    return buf.getvalue()
