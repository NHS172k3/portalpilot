# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2.0"]
# ///
"""Set a task status for local/demo verification."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[3]


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
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: set_task_status.py TASK_ID STATUS", file=sys.stderr)
        return 2
    load_env()
    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("SUPABASE_DB_URL/DATABASE_URL missing", file=sys.stderr)
        return 1
    task_id, status = sys.argv[1], sys.argv[2]
    with psycopg.connect(db_url, prepare_threshold=None, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("update filing_tasks set status = %s, blocker = null where id = %s", (status, task_id))
            cursor.execute("delete from field_records where task_id = %s", (task_id,))
            cursor.execute("delete from agent_events where task_id = %s", (task_id,))
            print(f"updated {cursor.rowcount} event rows after setting {task_id} to {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
