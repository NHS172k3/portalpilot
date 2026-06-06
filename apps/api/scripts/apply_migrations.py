# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2.0"]
# ///
"""Apply local SQL migrations through SUPABASE_DB_URL/DATABASE_URL."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"


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

    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))
    applied: list[str] = []

    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                for migration in migrations:
                    cur.execute(migration.read_text())
                    applied.append(migration.name)

                cur.execute(
                    """
                    select table_name
                    from information_schema.tables
                    where table_schema = 'public'
                      and table_name in (
                        'business_profiles',
                        'attributes',
                        'documents',
                        'extracted_facts',
                        'form_definitions',
                        'form_fields',
                        'filing_tasks',
                        'recommendations',
                        'field_records',
                        'agent_events'
                      )
                    order by table_name
                    """
                )
                tables = [row[0] for row in cur.fetchall()]
    except Exception as exc:  # noqa: BLE001 - operational script should report failures.
        print(json.dumps({"ok": False, "applied": applied, "reason": str(exc)}, indent=2))
        return 1

    print(json.dumps({"ok": len(tables) == 10, "applied": applied, "tables": tables}, indent=2))
    return 0 if len(tables) == 10 else 1


if __name__ == "__main__":
    sys.exit(main())
