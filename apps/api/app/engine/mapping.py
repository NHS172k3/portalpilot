from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Literal

from app.extraction import normalize_key


Sensitivity = Literal["public", "business", "personal", "confidential"]
FieldStatus = Literal["filled", "left_blank", "needs_review", "blocked", "user_required", "not_applicable"]

HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.5
SENSITIVE_VALUES = {"personal", "confidential"}


@dataclass(frozen=True)
class FormField:
    key: str
    label: str
    section: str
    type: str
    sensitivity: Sensitivity = "business"
    required: bool = False
    human_only: bool = False
    provenance: str = "agent_fillable"
    conditional_on: str | None = None


@dataclass(frozen=True)
class AvailableFact:
    key: str
    value: str
    source: str
    confidence: float = 1.0
    sensitivity: Sensitivity = "business"
    label: str | None = None


@dataclass(frozen=True)
class FieldRecord:
    field_key: str
    label: str
    section: str
    proposed_value: str | None
    sources: list[str] = field(default_factory=list)
    confidence: float = 0
    sensitivity: Sensitivity = "business"
    status: FieldStatus = "left_blank"
    reason: str = ""


def build_facts(
    attributes: list[dict],
    extracted_facts: list[dict] | None = None,
    task_context: dict[str, str] | None = None,
) -> list[AvailableFact]:
    facts: list[AvailableFact] = []
    for attribute in attributes:
        value = str(attribute.get("value") or "").strip()
        if not value:
            continue
        facts.append(
            AvailableFact(
                key=str(attribute.get("key") or normalize_key(str(attribute.get("label") or ""))),
                label=str(attribute.get("label") or ""),
                value=value,
                source=f"profile:{attribute.get('key')}",
                confidence=1.0,
                sensitivity=attribute.get("sensitivity", "business"),
            )
        )

    for fact in extracted_facts or []:
        value = str(fact.get("value") or "").strip()
        if not value:
            continue
        facts.append(
            AvailableFact(
                key=str(fact.get("key") or ""),
                label=str(fact.get("label") or fact.get("key") or ""),
                value=value,
                source=str(fact.get("source") or fact.get("document_id") or "document"),
                confidence=float(fact.get("confidence") or 0),
                sensitivity=fact.get("sensitivity", "business"),
            )
        )

    for key, value in (task_context or {}).items():
        if str(value).strip():
            facts.append(
                AvailableFact(
                    key=key,
                    label=key.replace("_", " "),
                    value=str(value),
                    source=f"context:{key}",
                    confidence=0.85,
                    sensitivity="business",
                )
            )

    return facts


def map_fields(fields: list[FormField], facts: list[AvailableFact]) -> list[FieldRecord]:
    records: list[FieldRecord] = []
    known_values = {normalize_key(fact.key): fact.value for fact in facts}
    for field_item in fields:
        if not condition_applies(field_item, known_values):
            records.append(
                FieldRecord(
                    field_key=field_item.key,
                    label=field_item.label,
                    section=field_item.section,
                    proposed_value=None,
                    sensitivity=field_item.sensitivity,
                    status="not_applicable",
                    reason="Field condition is not satisfied by available data.",
                )
            )
            continue
        record = map_field(field_item, facts)
        records.append(record)
        if record.proposed_value is not None:
            known_values[normalize_key(record.field_key)] = record.proposed_value
    return records


def map_field(field_item: FormField, facts: list[AvailableFact]) -> FieldRecord:
    if field_item.human_only:
        return FieldRecord(
            field_key=field_item.key,
            label=field_item.label,
            section=field_item.section,
            proposed_value=None,
            sensitivity=field_item.sensitivity,
            status="user_required" if field_item.required else "blocked",
            reason="Field is marked human-only in the form definition.",
        )

    if field_item.provenance == "retrieved":
        return FieldRecord(
            field_key=field_item.key,
            label=field_item.label,
            section=field_item.section,
            proposed_value=None,
            sensitivity=field_item.sensitivity,
            status="left_blank",
            reason="Field is marked as portal-retrieved in the form definition.",
        )

    match = best_fact(field_item, facts)
    if match is None:
        return FieldRecord(
            field_key=field_item.key,
            label=field_item.label,
            section=field_item.section,
            proposed_value=None,
            sensitivity=field_item.sensitivity,
            status="user_required" if field_item.required else "left_blank",
            reason="No confident source was found.",
        )

    fact, score = match
    confidence = round(min(fact.confidence, 1.0) * score, 3)
    if field_item.sensitivity in SENSITIVE_VALUES:
        return FieldRecord(
            field_key=field_item.key,
            label=field_item.label,
            section=field_item.section,
            proposed_value=None,
            sources=[fact.source],
            confidence=confidence,
            sensitivity=field_item.sensitivity,
            status="needs_review",
            reason="Sensitive field requires human review before filling.",
        )

    if confidence >= HIGH_CONFIDENCE:
        return FieldRecord(
            field_key=field_item.key,
            label=field_item.label,
            section=field_item.section,
            proposed_value=fact.value,
            sources=[fact.source],
            confidence=confidence,
            sensitivity=field_item.sensitivity,
            status="filled",
            reason="Matched to a high-confidence source.",
        )

    if confidence >= MEDIUM_CONFIDENCE and field_item.sensitivity == "business":
        return FieldRecord(
            field_key=field_item.key,
            label=field_item.label,
            section=field_item.section,
            proposed_value=fact.value,
            sources=[fact.source],
            confidence=confidence,
            sensitivity=field_item.sensitivity,
            status="needs_review",
            reason="Matched to a medium-confidence business source.",
        )

    return FieldRecord(
        field_key=field_item.key,
        label=field_item.label,
        section=field_item.section,
        proposed_value=None,
        sources=[fact.source],
        confidence=confidence,
        sensitivity=field_item.sensitivity,
        status="user_required" if field_item.required else "left_blank",
        reason="Matched source confidence is below the fill threshold.",
    )


def best_fact(field_item: FormField, facts: list[AvailableFact]) -> tuple[AvailableFact, float] | None:
    candidates: list[tuple[AvailableFact, float]] = []
    for fact in facts:
        score = match_score(field_item, fact)
        if score >= 0.45:
            candidates.append((fact, score))

    if not candidates:
        return None

    return max(candidates, key=lambda candidate: (candidate[1] * candidate[0].confidence, candidate[1]))


def condition_applies(field_item: FormField, known_values: dict[str, str]) -> bool:
    if not field_item.conditional_on:
        return True
    if "=" not in field_item.conditional_on:
        return False
    raw_key, raw_value = field_item.conditional_on.split("=", 1)
    expected = normalize_key(raw_value)
    actual = known_values.get(normalize_key(raw_key))
    if actual is None:
        return False
    return expected in {normalize_key(part) for part in str(actual).split(",")}


def match_score(field_item: FormField, fact: AvailableFact) -> float:
    field_key = normalize_key(field_item.key)
    field_label = normalize_key(field_item.label)
    fact_key = normalize_key(fact.key)
    fact_label = normalize_key(fact.label or fact.key)

    if field_key == fact_key:
        return 1.0
    if field_label == fact_key or field_key == fact_label:
        return 0.92
    if field_label == fact_label:
        return 0.88

    field_tokens = set(field_label.split("_")) | set(field_key.split("_"))
    fact_tokens = set(fact_label.split("_")) | set(fact_key.split("_"))
    token_overlap = len(field_tokens & fact_tokens) / max(len(field_tokens), 1)
    similarity = max(
        SequenceMatcher(a=field_label, b=fact_label).ratio(),
        SequenceMatcher(a=field_key, b=fact_key).ratio(),
    )
    return round(max(token_overlap * 0.75, similarity * 0.65), 3)
