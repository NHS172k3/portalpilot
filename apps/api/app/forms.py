from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import connect


router = APIRouter(prefix="/forms", tags=["forms"])
Db = Annotated[Connection, Depends(connect)]


@router.get("")
def list_forms(connection: Db) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
              d.id,
              d.jurisdiction,
              d.agency,
              d.name,
              d.portal_url,
              d.notes,
              count(f.id)::int as field_count
            from form_definitions d
            left join form_fields f on f.form_definition_id = d.id
            group by d.id
            order by d.name
            """
        )
        return cursor.fetchall()


@router.get("/{form_id}")
def get_form(form_id: str, connection: Db) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select id, jurisdiction, agency, name, portal_url, prerequisites, notes, created_at, updated_at
            from form_definitions
            where id = %s
            """,
            (form_id,),
        )
        form = cursor.fetchone()
        if form is None:
            raise HTTPException(status_code=404, detail="Form definition not found")

        cursor.execute(
            """
            select
              id,
              key,
              label,
              section,
              type,
              options,
              sensitivity,
              required,
              human_only,
              provenance,
              conditional_on,
              notes,
              position
            from form_fields
            where form_definition_id = %s
            order by coalesce(position, id), section, label
            """,
            (form_id,),
        )
        form["fields"] = cursor.fetchall()
        return form
