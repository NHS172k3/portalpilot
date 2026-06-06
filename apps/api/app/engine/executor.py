from __future__ import annotations

from dataclasses import dataclass

from app.engine.mapping import FormField
from app.engine.portal import Portal, PortalAction


DENIED_CONTROL_WORDS = {
    "authenticate",
    "captcha",
    "confirm submission",
    "credential",
    "declaration",
    "endorse",
    "login",
    "mfa",
    "otp",
    "password",
    "pay",
    "payment",
    "proceed to payment",
    "sign in",
    "submit",
}


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    reason: str
    action: PortalAction


class ActionExecutor:
    def __init__(self, fields: list[FormField]) -> None:
        self._fields_by_key = {field.key: field for field in fields}

    def execute(self, portal: Portal, action: PortalAction) -> ExecutionResult:
        blocked_reason = self.block_reason(action)
        if blocked_reason:
            return ExecutionResult(ok=False, reason=blocked_reason, action=action)

        if action.action == "fill" and action.field_key and action.value is not None:
            portal.fill(action.field_key, action.value)
        elif action.action == "select" and action.field_key and action.value is not None:
            portal.select(action.field_key, action.value)
        elif action.action == "navigate" and action.label:
            portal.navigate(action.label)
        elif action.action == "save_draft":
            portal.save_draft()
        else:
            return ExecutionResult(ok=False, reason="Action payload is incomplete.", action=action)

        return ExecutionResult(ok=True, reason="Action executed.", action=action)

    def block_reason(self, action: PortalAction) -> str | None:
        field = self._fields_by_key.get(action.field_key or "")
        label = " ".join(part for part in [action.label, action.field_key, action.value] if part).lower()

        if field and field.human_only:
            return "Target field is marked human-only in the form definition."

        if any(word in label for word in DENIED_CONTROL_WORDS):
            return "Control label matches a human-only action denylist."

        if action.action in {"fill", "select"} and not field:
            return "Target field is not present in the observed portal fields."

        return None
