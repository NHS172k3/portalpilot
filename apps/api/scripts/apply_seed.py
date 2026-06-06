# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2.0"]
# ///
"""Apply local SQL seed files through SUPABASE_DB_URL/DATABASE_URL."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = ROOT / "supabase" / "seed"
TABLES = (
    "business_profiles",
    "attributes",
    "documents",
    "extracted_facts",
    "form_definitions",
    "form_fields",
    "filing_tasks",
    "recommendations",
    "field_records",
    "agent_events",
)


def load_env() -> None:
    for filename in (".env", "apps/api/.env"):
        path = ROOT / filename
        if not path.exists():
            continue
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip(";").strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def main() -> int:
    load_env()
    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print(json.dumps({"ok": False, "reason": "SUPABASE_DB_URL/DATABASE_URL missing"}, indent=2))
        return 1

    seed_files = sorted(SEED_DIR.glob("*.sql"))
    applied: list[str] = []

    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                for seed_file in seed_files:
                    cur.execute(seed_file.read_text())
                    applied.append(seed_file.name)

                counts: dict[str, int] = {}
                for table in TABLES:
                    cur.execute(f"select count(*) from public.{table}")
                    counts[table] = int(cur.fetchone()[0])
    except Exception as exc:  # noqa: BLE001 - operational script should report failures.
        print(json.dumps({"ok": False, "applied": applied, "reason": str(exc)}, indent=2))
        return 1

    print(json.dumps({"ok": True, "applied": applied, "counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
