from app.engine.agent import MirrorAgent
from app.engine.mapping import AvailableFact, FormField


def test_mirror_agent_fills_safe_fields_and_leaves_human_only_blank() -> None:
    fields = [
        FormField("entity_name", "Entity name", "General", "text", "public", True, False),
        FormField("contact_email", "Contact email", "General", "text", "business", True, False),
        FormField("attestation", "Attestation", "Review", "checkbox", "confidential", True, True),
    ]
    facts = [
        AvailableFact("entity_name", "North Pier Studio", "profile:entity_name", 1, "public"),
        AvailableFact("contact_email", "hello@example.test", "document:summary", 0.72, "business"),
        AvailableFact("attestation", "yes", "profile:attestation", 1, "confidential"),
    ]

    result = MirrorAgent().run(fields, facts)
    records = {record.field_key: record for record in result.field_records}

    assert result.portal_values == {
        "entity_name": "North Pier Studio",
        "contact_email": "hello@example.test",
    }
    assert result.final_state == "ready_for_user_review"
    assert records["entity_name"].status == "filled"
    assert records["contact_email"].status == "needs_review"
    assert records["attestation"].status == "user_required"
    assert records["attestation"].proposed_value is None


def test_mirror_agent_skips_missing_required_field() -> None:
    result = MirrorAgent().run(
        [FormField("missing_reference", "Missing reference", "General", "text", "business", True, False)],
        [],
    )

    assert result.field_records[0].status == "user_required"
    assert result.portal_values == {}
    assert any(event["type"] == "field_skipped" for event in result.events)
