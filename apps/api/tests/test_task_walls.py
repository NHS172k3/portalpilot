from app.engine.mapping import FieldRecord, FormField
from app.tasks import _build_blocker


def test_builds_info_wall_for_missing_required_agent_field() -> None:
    fields = [FormField("reference", "Reference", "General", "text", "business", True, False)]
    records = [
        FieldRecord(
            field_key="reference",
            label="Reference",
            section="General",
            proposed_value=None,
            status="user_required",
            reason="No confident source was found.",
        )
    ]

    blocker = _build_blocker(fields, records)

    assert blocker is not None
    assert blocker["type"] == "info_required"
    assert blocker["needed_action"] == "provide_info"
    assert blocker["needed_fields"][0]["key"] == "reference"


def test_info_wall_takes_priority_over_human_only_boundary() -> None:
    fields = [
        FormField("reference", "Reference", "General", "text", "business", True, False),
        FormField("attestation", "Attestation", "Review", "checkbox", "confidential", True, True),
    ]
    records = [
        FieldRecord("reference", "Reference", "General", None, status="user_required"),
        FieldRecord("attestation", "Attestation", "Review", None, status="user_required"),
    ]

    blocker = _build_blocker(fields, records)

    assert blocker is not None
    assert blocker["type"] == "info_required"


def test_builds_auth_wall_when_only_human_only_fields_remain() -> None:
    fields = [FormField("attestation", "Attestation", "Review", "checkbox", "confidential", True, True)]
    records = [FieldRecord("attestation", "Attestation", "Review", None, status="user_required")]

    blocker = _build_blocker(fields, records)

    assert blocker is not None
    assert blocker["type"] == "auth_required"
    assert blocker["needed_action"] == "open_portal"
