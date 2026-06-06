from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol
from urllib.request import Request, urlopen

from app.engine.mapping import FieldRecord, FormField


PageState = Literal[
    "not_ready",
    "human_access_required",
    "fillable_section",
    "review_section",
    "legal_declaration_boundary",
    "submit_boundary",
    "blocked_or_unknown",
    "ready_for_user_review",
]


@dataclass(frozen=True)
class PortalAction:
    action: Literal["fill", "select", "navigate", "save_draft"]
    field_key: str | None = None
    value: str | None = None
    label: str | None = None


@dataclass
class PortalObservation:
    state: PageState
    fields: list[FormField] = field(default_factory=list)
    filled_values: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    title: str | None = None
    reason: str | None = None


class Portal(Protocol):
    def observe(self) -> PortalObservation: ...

    def classify_state(self) -> PageState: ...

    def list_fields(self) -> list[FormField]: ...

    def fill(self, field_key: str, value: str) -> None: ...

    def select(self, field_key: str, option: str) -> None: ...

    def navigate(self, action: str) -> None: ...

    def save_draft(self) -> None: ...


class MirrorPortal:
    def __init__(self, fields: list[FormField]) -> None:
        self._fields = fields
        self._values: dict[str, str] = {}
        self._state: PageState = "fillable_section"

    @property
    def values(self) -> dict[str, str]:
        return dict(self._values)

    def observe(self) -> PortalObservation:
        return PortalObservation(state=self._state, fields=self.list_fields(), filled_values=self.values)

    def classify_state(self) -> PageState:
        return self._state

    def list_fields(self) -> list[FormField]:
        return list(self._fields)

    def fill(self, field_key: str, value: str) -> None:
        self._values[field_key] = value

    def select(self, field_key: str, option: str) -> None:
        self._values[field_key] = option

    def navigate(self, action: str) -> None:
        if action == "review":
            self._state = "review_section"

    def save_draft(self) -> None:
        self._state = "ready_for_user_review"


class LivePortal:
    def __init__(self, portal_url: str, fields: list[FormField]) -> None:
        self.portal_url = portal_url
        self._fields = fields
        self._observation: PortalObservation | None = None

    def observe(self) -> PortalObservation:
        if self._observation is None:
            self._observation = self._observe_url()
        return self._observation

    def classify_state(self) -> PageState:
        return self.observe().state

    def list_fields(self) -> list[FormField]:
        return list(self._fields)

    def fill(self, field_key: str, value: str) -> None:
        raise RuntimeError("LivePortal does not fill before human access is cleared")

    def select(self, field_key: str, option: str) -> None:
        raise RuntimeError("LivePortal does not select before human access is cleared")

    def navigate(self, action: str) -> None:
        raise RuntimeError("LivePortal navigation is read-only during auth handoff")

    def save_draft(self) -> None:
        raise RuntimeError("LivePortal cannot save a draft before human access is cleared")

    def _observe_url(self) -> PortalObservation:
        try:
            request = Request(self.portal_url, headers={"User-Agent": "PortalPilot demo reachability check"})
            with urlopen(request, timeout=15) as response:
                body = response.read(120_000).decode("utf-8", errors="ignore")
                final_url = response.geturl()
        except Exception as exc:  # noqa: BLE001 - live portals fail in many ordinary ways.
            return PortalObservation(
                state="human_access_required",
                fields=self.list_fields(),
                url=self.portal_url,
                reason=f"Live portal requires human browser access: {exc}",
            )

        lowered = body.lower()
        wall_words = ("captcha", "login", "log in", "sign in", "authenticate", "singpass", "password", "mfa", "otp")
        title = _html_title(body)
        if any(word in lowered for word in wall_words):
            return PortalObservation(
                state="human_access_required",
                fields=self.list_fields(),
                url=final_url,
                title=title,
                reason="Live portal exposed an authentication or CAPTCHA boundary.",
            )
        return PortalObservation(
            state="blocked_or_unknown",
            fields=self.list_fields(),
            url=final_url,
            title=title,
            reason="Live portal reached, but no trusted fillable state was established.",
        )


def _html_title(body: str) -> str | None:
    start = body.lower().find("<title")
    if start < 0:
        return None
    start = body.find(">", start)
    end = body.lower().find("</title>", start)
    if start < 0 or end < 0:
        return None
    return " ".join(body[start + 1 : end].split())[:240]


def action_from_record(record: FieldRecord, field_type: str) -> PortalAction | None:
    if record.status not in {"filled", "needs_review"} or record.proposed_value is None:
        return None
    if field_type in {"select", "radio", "checkbox", "multi_select"}:
        return PortalAction(action="select", field_key=record.field_key, value=record.proposed_value, label=record.label)
    return PortalAction(action="fill", field_key=record.field_key, value=record.proposed_value, label=record.label)
