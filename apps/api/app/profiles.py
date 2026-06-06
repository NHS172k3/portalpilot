from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from psycopg import Connection

from app.database import connect
from app.extraction import extract_facts, extract_text_from_upload
from app.schemas import AttributeIn, ProfileIn, ProfilePatch


router = APIRouter(prefix="/profiles", tags=["profiles"])
Db = Annotated[Connection, Depends(connect)]


def ensure_profile(connection: Connection, profile_id: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("select 1 from business_profiles where id = %s", (profile_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Profile not found")


def read_profile(connection: Connection, profile_id: str) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select id, name, created_at, updated_at
            from business_profiles
            where id = %s
            """,
            (profile_id,),
        )
        profile = cursor.fetchone()
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        cursor.execute(
            """
            select id, key, label, value, sensitivity, notes, created_at, updated_at
            from attributes
            where business_profile_id = %s
            order by label, key
            """,
            (profile_id,),
        )
        profile["attributes"] = cursor.fetchall()
        return profile


@router.get("")
def list_profiles(connection: Db) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select
              p.id,
              p.name,
              p.created_at,
              p.updated_at,
              count(a.id)::int as attribute_count
            from business_profiles p
            left join attributes a on a.business_profile_id = p.id
            group by p.id
            order by p.created_at desc
            """
        )
        return cursor.fetchall()


@router.post("", status_code=201)
def create_profile(payload: ProfileIn, connection: Db) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into business_profiles (name)
            values (%s)
            returning id
            """,
            (payload.name,),
        )
        profile_id = cursor.fetchone()["id"]
    connection.commit()
    return read_profile(connection, profile_id)


@router.get("/{profile_id}")
def get_profile(profile_id: str, connection: Db) -> dict:
    return read_profile(connection, profile_id)


@router.patch("/{profile_id}")
def update_profile(profile_id: str, payload: ProfilePatch, connection: Db) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            update business_profiles
            set name = %s
            where id = %s
            returning id
            """,
            (payload.name, profile_id),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Profile not found")
    connection.commit()
    return read_profile(connection, profile_id)


@router.post("/{profile_id}/attributes", status_code=201)
def upsert_attribute(profile_id: str, payload: AttributeIn, connection: Db) -> dict:
    ensure_profile(connection, profile_id)
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
            returning id, key, label, value, sensitivity, notes, created_at, updated_at
            """,
            (profile_id, payload.key, payload.label, payload.value, payload.sensitivity, payload.notes),
        )
        attribute = cursor.fetchone()
    connection.commit()
    return attribute


@router.delete("/{profile_id}/attributes/{key}", status_code=204)
def delete_attribute(profile_id: str, key: str, connection: Db) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            delete from attributes
            where business_profile_id = %s and key = %s
            """,
            (profile_id, key),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Attribute not found")
    connection.commit()


@router.get("/{profile_id}/documents")
def list_documents(profile_id: str, connection: Db) -> list[dict]:
    ensure_profile(connection, profile_id)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select id, filename, mime, blob_ref, created_at
            from documents
            where business_profile_id = %s
            order by created_at desc
            """,
            (profile_id,),
        )
        documents = cursor.fetchall()
        for document in documents:
            cursor.execute(
                """
                select id, key, value, evidence_note, confidence, sensitivity, expiry_marker, created_at
                from extracted_facts
                where document_id = %s
                order by confidence desc, created_at desc
                """,
                (document["id"],),
            )
            document["facts"] = cursor.fetchall()
        return documents


@router.post("/{profile_id}/documents", status_code=201)
async def upload_document(profile_id: str, connection: Db, file: UploadFile = File(...)) -> dict:
    ensure_profile(connection, profile_id)
    content = await file.read()
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail="Document exceeds the 2 MB demo limit")

    mime = file.content_type or "application/octet-stream"
    text = extract_text_from_upload(file.filename or "document", mime, content)
    facts = extract_facts(text)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into documents (business_profile_id, filename, mime, blob_ref)
            values (%s, %s, %s, %s)
            returning id, filename, mime, blob_ref, created_at
            """,
            (profile_id, file.filename or "document", mime, f"session://{profile_id}/{file.filename or 'document'}"),
        )
        document = cursor.fetchone()

        inserted_facts = []
        for fact in facts:
            cursor.execute(
                """
                insert into extracted_facts (
                  business_profile_id,
                  document_id,
                  source,
                  key,
                  value,
                  evidence_note,
                  confidence,
                  sensitivity
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                returning id, key, value, evidence_note, confidence, sensitivity, expiry_marker, created_at
                """,
                (
                    profile_id,
                    document["id"],
                    document["filename"],
                    fact.key,
                    fact.value,
                    fact.evidence_note,
                    fact.confidence,
                    fact.sensitivity,
                ),
            )
            inserted_facts.append(cursor.fetchone())

    connection.commit()
    document["facts"] = inserted_facts
    return document
