from app.engine.executor import ActionExecutor
from app.engine.mapping import FormField
from app.engine.portal import MirrorPortal, PortalAction


def test_executor_blocks_human_only_field() -> None:
    fields = [
        FormField(
            key="attestation",
            label="Attestation",
            section="Review",
            type="checkbox",
            sensitivity="confidential",
            required=True,
            human_only=True,
        )
    ]
    portal = MirrorPortal(fields)
    result = ActionExecutor(fields).execute(
        portal,
        PortalAction(action="select", field_key="attestation", value="yes", label="Attestation"),
    )

    assert result.ok is False
    assert portal.values == {}
    assert "human-only" in result.reason


def test_executor_blocks_injected_final_action() -> None:
    fields = [FormField("entity_name", "Entity name", "General", "text", "public", True, False)]
    portal = MirrorPortal(fields)
    result = ActionExecutor(fields).execute(
        portal,
        PortalAction(action="navigate", label="Submit final application"),
    )

    assert result.ok is False
    assert result.reason == "Control label matches a human-only action denylist."


def test_executor_allows_safe_fill() -> None:
    fields = [FormField("entity_name", "Entity name", "General", "text", "public", True, False)]
    portal = MirrorPortal(fields)
    result = ActionExecutor(fields).execute(
        portal,
        PortalAction(action="fill", field_key="entity_name", value="North Pier Studio", label="Entity name"),
    )

    assert result.ok is True
    assert portal.values == {"entity_name": "North Pier Studio"}
