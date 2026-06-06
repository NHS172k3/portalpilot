from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import connect
from app.engine.agent import MirrorAgent
from app.engine.mapping import FieldRecord, FormField, build_facts
from app.engine.portal import LivePortal
from app.schemas import ResolveInfoIn


router = APIRouter(prefix="/tasks", tags=["tasks"])
Db = Annotated[Connection, Depends(connect)]


@router.get("")
def list_tasks(connection: Db) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
              t.id,
              t.business_profile_id,
              t.status,
              t.origin,
              t.blocker,
              t.notes,
              t.created_at,
              t.updated_at,
              p.name as profile_name,
              d.name as form_name,
              d.agency,
              d.jurisdiction,
              d.id as form_definition_id
            from filing_tasks t
            join business_profiles p on p.id = t.business_profile_id
            left join form_definitions d on d.id = t.form_definition_id
            order by t.updated_at desc, t.created_at desc
            """
        )
        return cursor.fetchall()


@router.get("/{task_id}")
def get_task(task_id: str, connection: Db) -> dict:
    task = _load_task_detail(connection, task_id)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select field_key, label, section, proposed_value, sources, confidence, sensitivity, status, reason, updated_at
            from field_records
            where task_id = %s
            order by section, label
            """,
            (task_id,),
        )
        task["field_records"] = cursor.fetchall()
        cursor.execute(
            """
            select type, payload, timestamp
            from agent_events
            where task_id = %s
            order by timestamp desc, id desc
            limit 80
            """,
            (task_id,),
        )
        task["agent_events"] = cursor.fetchall()
        cursor.execute(
            """
            select reason, prerequisites, fee, timeline, warnings, source_links, confidence, created_at
            from recommendations
            where task_id = %s
            """,
            (task_id,),
        )
        task["recommendation"] = cursor.fetchone()
    return task


@router.post("/{task_id}/run-mirror-agent")
def run_mirror_agent(task_id: str, connection: Db) -> dict:
    return run_task_on_mirror(task_id, connection)


@router.post("/{task_id}/run-live-agent")
def run_live_agent(task_id: str, connection: Db) -> dict:
    task = _load_task_with_form(connection, task_id)
    portal_url = task.get("portal_url")
    if not portal_url:
        raise HTTPException(status_code=400, detail="Task form has no live portal URL")

    fields = _load_fields(connection, task["form_definition_id"])
    portal = LivePortal(portal_url, fields)
    observation = portal.observe()
    blocker = {
        "type": "auth_required",
        "message": "Live portal access requires a human login or CAPTCHA step.",
        "needed_action": "open_portal",
        "portal_url": observation.url or portal_url,
        "needed_fields": [],
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update filing_tasks
            set status = 'action_required',
                blocker = %s::jsonb
            where id = %s
            """,
            (_json(blocker), task_id),
        )
        cursor.execute(
            """
            insert into agent_events (task_id, type, payload)
            values (%s, 'live_portal_reached', %s::jsonb)
            """,
            (
                task_id,
                _json(
                    {
                        "state": observation.state,
                        "url": observation.url,
                        "title": observation.title,
                        "reason": observation.reason,
                    }
                ),
            ),
        )
        cursor.execute(
            """
            insert into agent_events (task_id, type, payload)
            values (%s, 'wall_raised', %s::jsonb)
            """,
            (task_id, _json(blocker)),
        )
    connection.commit()
    return {"task_id": task_id, "status": "action_required", "observation": asdict(observation), "blocker": blocker}


@router.post("/{task_id}/resume-after-auth")
def resume_after_auth(task_id: str, connection: Db) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into agent_events (task_id, type, payload)
            values (%s, 'resumed', %s::jsonb)
            """,
            (task_id, _json({"source": "human_auth_handoff"})),
        )
    connection.commit()
    return run_task_on_mirror(task_id, connection)


@router.post("/{task_id}/resolve-info")
def resolve_info(task_id: str, payload: ResolveInfoIn, connection: Db) -> dict:
    task = _load_task(connection, task_id)
    if task["form_definition_id"] is None:
        raise HTTPException(status_code=400, detail="Task has no form definition")

    field = _load_field(connection, task["form_definition_id"], payload.field_key)
    value = payload.value.strip()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into attributes (business_profile_id, key, label, value, sensitivity, notes)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (business_profile_id, key) do update
            set label = excluded.label,
                value = excluded.value,
                sensitivity = excluded.sensitivity,
                notes = excluded.notes
            """,
            (
                task["business_profile_id"],
                field.key,
                field.label,
                value,
                field.sensitivity,
                "User supplied to resolve an Action Required task.",
            ),
        )
        cursor.execute(
            """
            insert into agent_events (task_id, type, payload)
            values (%s, 'wall_resolved', %s::jsonb)
            """,
            (task_id, _json({"field_key": field.key, "label": field.label, "source": "user_supplied"})),
        )
    connection.commit()
    return run_task_on_mirror(task_id, connection)


@router.post("/{task_id}/complete-review")
def complete_review(task_id: str, connection: Db) -> dict:
    task = _load_task(connection, task_id)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update filing_tasks
            set status = 'completed', blocker = null
            where id = %s
            """,
            (task_id,),
        )
        cursor.execute(
            """
            insert into agent_events (task_id, type, payload)
            values (%s, 'review_completed', %s::jsonb)
            """,
            (task_id, _json({"previous_status": task["status"]})),
        )
    connection.commit()
    return _load_task_detail(connection, task_id)


def run_task_on_mirror(task_id: str, connection: Connection) -> dict:
    task = _load_task(connection, task_id)
    if task["form_definition_id"] is None:
        raise HTTPException(status_code=400, detail="Task has no form definition")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            update filing_tasks
            set status = 'in_progress', blocker = null
            where id = %s
            """,
            (task_id,),
        )
        cursor.execute(
            """
            insert into agent_events (task_id, type, payload)
            values (%s, 'task_picked_up', '{}'::jsonb)
            """,
            (task_id,),
        )
    connection.commit()

    fields = _load_fields(connection, task["form_definition_id"])
    facts = build_facts(
        attributes=_load_attributes(connection, task["business_profile_id"]),
        extracted_facts=_load_extracted_facts(connection, task["business_profile_id"]),
        task_context={"task_origin": task["origin"]},
    )
    result = MirrorAgent().run(fields, facts)

    with connection.cursor() as cursor:
        cursor.execute("delete from field_records where task_id = %s", (task_id,))
        for record in result.field_records:
            cursor.execute(
                """
                insert into field_records (
                  task_id,
                  field_key,
                  label,
                  section,
                  proposed_value,
                  sources,
                  confidence,
                  sensitivity,
                  status,
                  reason
                )
                values (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                """,
                (
                    task_id,
                    record.field_key,
                    record.label,
                    record.section,
                    record.proposed_value,
                    _json(record.sources),
                    record.confidence,
                    record.sensitivity,
                    record.status,
                    record.reason,
                ),
            )

        for event in result.events:
            cursor.execute(
                """
                insert into agent_events (task_id, type, payload)
                values (%s, %s, %s::jsonb)
                """,
                (task_id, event["type"], _json(event["payload"])),
            )

        next_status = "in_progress"
        blocker = _build_blocker(fields, result.field_records)
        if blocker is not None:
            next_status = "action_required"
            cursor.execute(
                """
                insert into agent_events (task_id, type, payload)
                values (%s, 'wall_raised', %s::jsonb)
                """,
                (task_id, _json(blocker)),
            )
        else:
            cursor.execute(
                """
                insert into agent_events (task_id, type, payload)
                values (%s, 'ready_for_review', %s::jsonb)
                """,
                (task_id, _json({"message": "Agent filled available fields up to the review boundary."})),
            )

        cursor.execute(
            """
            update filing_tasks
            set status = %s,
                blocker = %s::jsonb
            where id = %s
            """,
            (next_status, _json(blocker) if blocker is not None else None, task_id),
        )

    connection.commit()
    return {
        "task_id": task_id,
        "status": next_status,
        "final_state": result.final_state,
        "filled": sum(1 for record in result.field_records if record.status == "filled"),
        "needs_review": sum(1 for record in result.field_records if record.status == "needs_review"),
        "user_required": sum(1 for record in result.field_records if record.status == "user_required"),
        "blocked": sum(1 for event in result.events if event["type"] == "action_blocked"),
        "portal_values": result.portal_values,
    }


def _build_blocker(fields: list[FormField], records: list[FieldRecord]) -> dict | None:
    field_by_key = {field.key: field for field in fields}
    info_needed = [
        record
        for record in records
        if record.status == "user_required" and not field_by_key.get(record.field_key, FormField(record.field_key, record.label, record.section, "text")).human_only
    ]
    if info_needed:
        record = info_needed[0]
        return {
            "type": "info_required",
            "message": f"Need {record.label} before the agent can continue.",
            "needed_action": "provide_info",
            "needed_fields": [
                {
                    "key": item.field_key,
                    "label": item.label,
                    "section": item.section,
                    "reason": item.reason,
                }
                for item in info_needed[:5]
            ],
        }

    auth_needed = [record for record in records if record.status == "user_required" and field_by_key.get(record.field_key) and field_by_key[record.field_key].human_only]
    if auth_needed:
        record = auth_needed[0]
        return {
            "type": "auth_required",
            "message": f"Human action required for {record.label}.",
            "needed_action": "open_portal",
            "needed_fields": [
                {
                    "key": item.field_key,
                    "label": item.label,
                    "section": item.section,
                    "reason": item.reason,
                }
                for item in auth_needed[:5]
            ],
        }
    return None


def _load_task_detail(connection: Connection, task_id: str) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
              t.id,
              t.business_profile_id,
              t.form_definition_id,
              t.status,
              t.origin,
              t.blocker,
              t.notes,
              t.created_at,
              t.updated_at,
              p.name as profile_name,
              d.name as form_name,
              d.agency,
              d.jurisdiction
            from filing_tasks t
            join business_profiles p on p.id = t.business_profile_id
            left join form_definitions d on d.id = t.form_definition_id
            where t.id = %s
            """,
            (task_id,),
        )
        task = cursor.fetchone()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task


def _load_task(connection: Connection, task_id: str) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select id, business_profile_id, form_definition_id, status, origin
            from filing_tasks
            where id = %s
            """,
            (task_id,),
        )
        task = cursor.fetchone()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task


def _load_task_with_form(connection: Connection, task_id: str) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
              t.id,
              t.business_profile_id,
              t.form_definition_id,
              t.status,
              t.origin,
              d.portal_url
            from filing_tasks t
            join form_definitions d on d.id = t.form_definition_id
            where t.id = %s
            """,
            (task_id,),
        )
        task = cursor.fetchone()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task


def _load_fields(connection: Connection, form_id: str) -> list[FormField]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select key, label, section, type, sensitivity, required, human_only, provenance, conditional_on
            from form_fields
            where form_definition_id = %s
            order by coalesce(position, id), section, label
            """,
            (form_id,),
        )
        return [FormField(**row) for row in cursor.fetchall()]


def _load_field(connection: Connection, form_id: str, field_key: str) -> FormField:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select key, label, section, type, sensitivity, required, human_only, provenance, conditional_on
            from form_fields
            where form_definition_id = %s and key = %s
            """,
            (form_id, field_key),
        )
        field = cursor.fetchone()
        if field is None:
            raise HTTPException(status_code=404, detail="Field not found")
        return FormField(**field)


def _load_attributes(connection: Connection, profile_id: str) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select key, label, value, sensitivity, notes
            from attributes
            where business_profile_id = %s
            """,
            (profile_id,),
        )
        return cursor.fetchall()


def _load_extracted_facts(connection: Connection, profile_id: str) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select key, value, source, confidence, sensitivity, evidence_note
            from extracted_facts
            where business_profile_id = %s
            """,
            (profile_id,),
        )
        return cursor.fetchall()


def _json(value: object) -> str:
    import json

    return json.dumps(value, default=str)
