from __future__ import annotations

from dataclasses import asdict, dataclass

from app.engine.executor import ActionExecutor, ExecutionResult
from app.engine.mapping import AvailableFact, FieldRecord, FormField, map_fields
from app.engine.portal import MirrorPortal, PortalAction, action_from_record


@dataclass
class AgentRunResult:
    field_records: list[FieldRecord]
    events: list[dict]
    portal_values: dict[str, str]
    final_state: str


class MirrorAgent:
    def run(self, fields: list[FormField], facts: list[AvailableFact]) -> AgentRunResult:
        portal = MirrorPortal(fields)
        executor = ActionExecutor(fields)
        events: list[dict] = [{"type": "portal_observed", "payload": asdict(portal.observe())}]
        records = map_fields(fields, facts)
        field_type_by_key = {field.key: field.type for field in fields}

        for record in records:
            action = action_from_record(record, field_type_by_key.get(record.field_key, "text"))
            if action is None:
                events.append({"type": "field_skipped", "payload": asdict(record)})
                continue

            result = executor.execute(portal, action)
            events.append(_event_from_execution(result, record))

        save_result = executor.execute(portal, PortalAction(action="save_draft", label="save draft"))
        events.append({"type": "draft_saved" if save_result.ok else "action_blocked", "payload": asdict(save_result)})

        return AgentRunResult(
            field_records=records,
            events=events,
            portal_values=portal.values,
            final_state=portal.classify_state(),
        )


def _event_from_execution(result: ExecutionResult, record: FieldRecord) -> dict:
    if result.ok:
        return {"type": "field_filled", "payload": {"record": asdict(record), "action": asdict(result.action)}}
    return {
        "type": "action_blocked",
        "payload": {"record": asdict(record), "action": asdict(result.action), "reason": result.reason},
    }
