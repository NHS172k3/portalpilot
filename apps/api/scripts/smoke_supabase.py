# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2.0"]
# ///
"""Phase 0 Supabase smoke checks.

The service-role key can insert rows into existing tables through PostgREST, but
it cannot create an arbitrary scratch table. For the required temp-row check,
provide SUPABASE_DB_URL or DATABASE_URL. The script still verifies REST reach
when only SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are present.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import psycopg


def load_env() -> None:
    for filename in (".env", "apps/api/.env"):
        path = Path(filename)
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


def check_rest() -> dict[str, Any]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return {"ok": False, "reason": "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing"}

    req = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/",
        method="GET",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return {"ok": 200 <= response.status < 300, "status": response.status}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "reason": exc.read().decode("utf-8", errors="replace")[:300]}
    except Exception as exc:  # noqa: BLE001 - smoke script should report all failures.
        return {"ok": False, "reason": str(exc)}


def check_db_row() -> dict[str, Any]:
    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        return {
            "ok": False,
            "reason": "SUPABASE_DB_URL/DATABASE_URL missing; cannot create a temp row before schema exists",
        }

    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                create table if not exists portalpilot_smoke_checks (
                  id text primary key,
                  value text not null,
                  created_at timestamptz not null default now()
                )
                """
            )
            cur.execute(
                """
                insert into portalpilot_smoke_checks (id, value)
                values ('phase0', 'ok')
                on conflict (id) do update set value = excluded.value
                returning id, value
                """
            )
            inserted = cur.fetchone()
            cur.execute("select id, value from portalpilot_smoke_checks where id = 'phase0'")
            selected = cur.fetchone()
            cur.execute("delete from portalpilot_smoke_checks where id = 'phase0'")

    return {"ok": inserted == selected == ("phase0", "ok"), "inserted": inserted, "selected": selected}


def main() -> int:
    load_env()
    report = {"rest": check_rest()}
    try:
        report["temp_row"] = check_db_row()
    except Exception as exc:  # noqa: BLE001 - smoke script should report all failures.
        report["temp_row"] = {"ok": False, "reason": str(exc)}

    print(json.dumps(report, indent=2, default=str))
    return 0 if report["rest"]["ok"] and report["temp_row"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
