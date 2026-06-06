"""Generality smoke check: insert a different form definition and run it."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import ResolveInfoIn
from app.tasks import complete_review, resolve_info, run_task_on_mirror


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
    load_env()
    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("SUPABASE_DB_URL/DATABASE_URL missing", file=sys.stderr)
        return 1

    suffix = uuid4().hex[:10]
    profile_id = f"general_profile_{suffix}"
    form_id = f"general_form_{suffix}"
    task_id = f"general_task_{suffix}"

    with psycopg.connect(db_url, row_factory=dict_row, prepare_threshold=None) as connection:
        try:
            with connection.cursor() as cursor:
                cursor.execute("insert into business_profiles (id, name) values (%s, %s)", (profile_id, "Generic bakery profile"))
                cursor.execute(
                    """
                    insert into attributes (business_profile_id, key, label, value, sensitivity)
                    values (%s, 'premises_name', 'Premises name', 'North Pier Bakery', 'business')
                    """,
                    (profile_id,),
                )
                cursor.execute(
                    """
                    insert into form_definitions (id, jurisdiction, agency, name, portal_url)
                    values (%s, 'TEST', 'Municipal Licensing Office', 'Temporary food stall permit', 'https://example.gov.test')
                    """,
                    (form_id,),
                )
                cursor.execute(
                    """
                    insert into form_fields (
                      form_definition_id,
                      key,
                      label,
                      section,
                      type,
                      sensitivity,
                      required,
                      human_only,
                      provenance,
                      position
                    )
                    values
                      (%s, 'premises_name', 'Premises name', 'Applicant', 'text', 'business', true, false, 'agent_fillable', 1),
                      (%s, 'operating_date', 'Operating date', 'Schedule', 'date', 'business', true, false, 'agent_fillable', 2),
                      (%s, 'final_attestation', 'Final attestation', 'Review', 'checkbox', 'confidential', true, true, 'human_only', 3)
                    """,
                    (form_id, form_id, form_id),
                )
                cursor.execute(
                    """
                    insert into filing_tasks (id, business_profile_id, form_definition_id, status, origin, notes)
                    values (%s, %s, %s, 'not_started', 'manual', 'Temporary generality task')
                    """,
                    (task_id, profile_id, form_id),
                )
            connection.commit()

            first = run_task_on_mirror(task_id, connection)
            if first["status"] != "action_required":
                raise RuntimeError(f"expected action_required for missing generic field, got {first['status']}")
            if first["filled"] != 1:
                raise RuntimeError(f"expected one generic field filled, got {first['filled']}")

            resumed = resolve_info(task_id, ResolveInfoIn(field_key="operating_date", value="2026-07-01"), connection)
            if resumed["status"] != "action_required":
                raise RuntimeError(f"expected human-only wall after supplied info, got {resumed['status']}")

            completed = complete_review(task_id, connection)
            if completed["status"] != "completed":
                raise RuntimeError(f"expected completed after review, got {completed['status']}")

            print(
                {
                    "task_id": task_id,
                    "first_status": first["status"],
                    "resumed_status": resumed["status"],
                    "completed_status": completed["status"],
                    "filled_first_run": first["filled"],
                }
            )
            return 0
        finally:
            with connection.cursor() as cursor:
                cursor.execute("delete from business_profiles where id = %s", (profile_id,))
            connection.commit()


if __name__ == "__main__":
    sys.exit(main())
