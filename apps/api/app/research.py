from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.config import get_settings
from app.database import connect
from app.schemas import AutoSuggestIn, ManualResearchIn


API_ROOT = "https://api.openai.com/v1"
router = APIRouter(prefix="/research", tags=["research"])
Db = Annotated[Connection, Depends(connect)]


@dataclass(frozen=True)
class ResearchRecommendation:
    title: str
    reason: str
    prerequisites: list[str] = field(default_factory=list)
    fee: str | None = None
    timeline: str | None = None
    warnings: list[str] = field(default_factory=list)
    source_links: list[dict[str, str]] = field(default_factory=list)
    confidence: float = 0.6


@router.post("/auto-suggest")
def auto_suggest(payload: AutoSuggestIn, connection: Db) -> dict:
    attributes = _load_profile_attributes(connection, payload.profile_id)
    profile_summary = "\n".join(
        f"- {row['label']}: {row['value']} ({row['sensitivity']})" for row in attributes[:40]
    )
    prompt = f"""
You are researching government filing obligations for one business profile.
Use web search and rely only on official government or regulator sources.
Return JSON only, with a top-level "recommendations" array of 1 to 3 items.
Each item must have: title, reason, prerequisites, fee, timeline, warnings,
source_links as [{{"title": "...", "url": "..."}}], and confidence from 0 to 1.
Do not include legal advice; phrase uncertain items as evaluations/checks.

Business profile:
{profile_summary}
"""
    recommendations = _research_recommendations(prompt)
    created = [_create_task_with_recommendation(connection, payload.profile_id, item, "auto_suggested") for item in recommendations]
    connection.commit()
    return {"created": created, "count": len(created)}


@router.post("/manual-add")
def manual_add(payload: ManualResearchIn, connection: Db) -> dict:
    _ensure_profile(connection, payload.profile_id)
    prompt = f"""
Research this government filing need using web search and only official government
or regulator sources. Return JSON only, with a top-level "recommendations" array
containing exactly 1 item. The item must have: title, reason, prerequisites, fee,
timeline, warnings, source_links as [{{"title": "...", "url": "..."}}], and
confidence from 0 to 1.

Filing need:
{payload.filing_need}
"""
    recommendation = _research_recommendations(prompt)[0]
    task = _create_task_with_recommendation(connection, payload.profile_id, recommendation, "manual")
    connection.commit()
    return task


def _research_recommendations(prompt: str) -> list[ResearchRecommendation]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is missing")

    response = _request_json(
        settings.openai_api_key,
        {
            "model": settings.openai_research_model,
            "input": prompt,
            "tools": [{"type": "web_search"}],
            "max_output_tokens": 1200,
            "store": False,
        },
    )
    text = _response_text(response)
    try:
        payload = json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Research response was not valid JSON") from exc

    rows = payload.get("recommendations")
    if not isinstance(rows, list) or not rows:
        raise HTTPException(status_code=502, detail="Research response did not include recommendations")
    recommendations = [_coerce_recommendation(row) for row in rows]
    grounded = [item for item in recommendations if item.source_links]
    if not grounded:
        raise HTTPException(status_code=502, detail="Research response did not include official source links")
    return grounded[:3]


def _request_json(api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API_ROOT}/responses",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=502, detail=f"Research request failed: HTTP {exc.code}: {detail}") from exc


def _response_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(content["text"])
    text = response.get("output_text") or "\n".join(parts)
    if not text.strip():
        raise HTTPException(status_code=502, detail="Research response was empty")
    return text


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    return match.group(1).strip() if match else stripped


def _coerce_recommendation(row: Any) -> ResearchRecommendation:
    if not isinstance(row, dict):
        raise HTTPException(status_code=502, detail="Research item was not an object")
    links = row.get("source_links") or []
    return ResearchRecommendation(
        title=str(row.get("title") or "Research-backed filing").strip()[:240],
        reason=str(row.get("reason") or "").strip(),
        prerequisites=_coerce_string_list(row.get("prerequisites"))[:8],
        fee=str(row.get("fee")).strip() if row.get("fee") is not None else None,
        timeline=str(row.get("timeline")).strip() if row.get("timeline") is not None else None,
        warnings=_coerce_string_list(row.get("warnings"))[:8],
        source_links=[
            {"title": str(link.get("title") or link.get("url") or "Source"), "url": str(link.get("url") or "")}
            for link in links
            if isinstance(link, dict) and _is_official_source(str(link.get("url") or ""))
        ][:6],
        confidence=max(0, min(float(row.get("confidence") or 0.6), 1)),
    )


def _is_official_source(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    host = host.lower()
    return (
        host.endswith(".gov")
        or ".gov." in host
        or host.endswith(".gov.sg")
        or host.endswith(".gob.mx")
        or host.endswith(".gc.ca")
        or host.endswith(".europa.eu")
    )


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _create_task_with_recommendation(
    connection: Connection,
    profile_id: str,
    recommendation: ResearchRecommendation,
    origin: str,
) -> dict:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into filing_tasks (business_profile_id, form_definition_id, status, origin, notes)
            values (%s, null, 'not_started', %s, %s)
            returning id, status, origin, notes
            """,
            (profile_id, origin, recommendation.title),
        )
        task = cursor.fetchone()
        cursor.execute(
            """
            insert into recommendations (
              task_id, reason, prerequisites, fee, timeline, warnings, source_links, confidence
            )
            values (%s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb, %s)
            """,
            (
                task["id"],
                recommendation.reason,
                json.dumps(recommendation.prerequisites),
                recommendation.fee,
                recommendation.timeline,
                json.dumps(recommendation.warnings),
                json.dumps(recommendation.source_links),
                recommendation.confidence,
            ),
        )
        cursor.execute(
            """
            insert into agent_events (task_id, type, payload)
            values (%s, 'research_done', %s::jsonb)
            """,
            (task["id"], json.dumps({"source_count": len(recommendation.source_links)})),
        )
    task["recommendation"] = recommendation.__dict__
    return task


def _ensure_profile(connection: Connection, profile_id: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("select 1 from business_profiles where id = %s", (profile_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Profile not found")


def _load_profile_attributes(connection: Connection, profile_id: str) -> list[dict]:
    _ensure_profile(connection, profile_id)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select label, value, sensitivity
            from attributes
            where business_profile_id = %s
            order by label
            """,
            (profile_id,),
        )
        return cursor.fetchall()
