"""Export businesses + meetings from Postgres to an xlsx file.

Usage: python scripts/export_xlsx.py [output.xlsx]
Reads DATABASE_URL from ../.env (same as the API).
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "backend"))
from db import database_url  # loads .env

out = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "exports" / f"clients_{datetime.now():%Y%m%d_%H%M}.xlsx"
out.parent.mkdir(parents=True, exist_ok=True)

conn = psycopg2.connect(database_url())

businesses = pd.read_sql(
    """
    SELECT b.id, b.name AS business_name, b.phone, b.email, b.website,
           b.business_type, b.city, b.country, b.channel, b.status,
           (SELECT min(m.scheduled_at) FROM meetings m
             WHERE m.business_id = b.id AND NOT m.done AND m.scheduled_at >= now()) AS next_meeting,
           b.notes, b.created_at
    FROM businesses b ORDER BY b.created_at
    """,
    conn,
)
meetings = pd.read_sql(
    """
    SELECT m.id, b.name AS business_name, m.scheduled_at, m.done, m.notes
    FROM meetings m JOIN businesses b ON b.id = m.business_id
    ORDER BY m.scheduled_at
    """,
    conn,
)
conn.close()

# Excel can't store tz-aware datetimes.
for df in (businesses, meetings):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None) if df[col].dt.tz is None else df[col].dt.tz_convert(None)

summary = (
    businesses.groupby("status").size().reset_index(name="count").sort_values("count", ascending=False)
)

with pd.ExcelWriter(out, engine="openpyxl") as xw:
    businesses.to_excel(xw, "Businesses", index=False)
    meetings.to_excel(xw, "Meetings", index=False)
    summary.to_excel(xw, "Summary", index=False)
    for ws in xw.book.worksheets:
        ws.freeze_panes = "A2"
        for col in ws.columns:
            width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 50)

print(f"Wrote {out} ({len(businesses)} businesses, {len(meetings)} meetings)")
