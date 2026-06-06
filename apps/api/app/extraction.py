from __future__ import annotations

import re
from dataclasses import dataclass


KEY_VALUE_RE = re.compile(r"^\s*([^:=\n]{2,80})\s*[:=]\s*(.{1,500})\s*$")


@dataclass(frozen=True)
class ExtractedFact:
    key: str
    value: str
    evidence_note: str
    confidence: float
    sensitivity: str = "business"


def normalize_key(label: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return normalized[:80] or "document_fact"


def extract_text_from_upload(filename: str, mime: str | None, content: bytes) -> str:
    content_type = mime or ""
    if content_type.startswith("text/") or filename.lower().endswith((".txt", ".md", ".csv")):
        return content.decode("utf-8", errors="replace")

    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""

        from io import BytesIO

        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return content.decode("utf-8", errors="ignore")


def extract_facts(text: str, *, fallback_key: str = "document_summary") -> list[ExtractedFact]:
    facts: list[ExtractedFact] = []
    for index, line in enumerate(text.splitlines(), start=1):
        match = KEY_VALUE_RE.match(line)
        if not match:
            continue

        label, value = match.groups()
        value = value.strip()
        if not value:
            continue

        facts.append(
            ExtractedFact(
                key=normalize_key(label),
                value=value,
                evidence_note=f"Line {index} in uploaded document",
                confidence=0.72,
            )
        )

    if facts:
        return facts[:40]

    compact = " ".join(text.split())
    if not compact:
        return []

    return [
        ExtractedFact(
            key=fallback_key,
            value=compact[:500],
            evidence_note="Document text summary",
            confidence=0.4,
        )
    ]
