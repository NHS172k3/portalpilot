from app.engine.mapping import AvailableFact, FormField, build_facts, map_field, map_fields


def test_fills_high_confidence_public_field() -> None:
    record = map_field(
        FormField(
            key="trading_name",
            label="Trading name",
            section="General",
            type="text",
            sensitivity="public",
            required=True,
        ),
        [
            AvailableFact(
                key="trading_name",
                label="Trading name",
                value="North Pier Studio",
                source="profile:trading_name",
                confidence=1,
                sensitivity="public",
            )
        ],
    )

    assert record.status == "filled"
    assert record.proposed_value == "North Pier Studio"
    assert record.confidence == 1


def test_medium_confidence_business_field_is_flagged() -> None:
    record = map_field(
        FormField(
            key="annual_turnover",
            label="Annual turnover",
            section="Operations",
            type="number",
            sensitivity="business",
            required=True,
        ),
        [
            AvailableFact(
                key="annual_turnover",
                value="120000",
                source="document:note",
                confidence=0.72,
                sensitivity="business",
            )
        ],
    )

    assert record.status == "needs_review"
    assert record.proposed_value == "120000"
    assert record.reason.startswith("Matched to a medium-confidence")


def test_low_confidence_required_field_is_left_for_user() -> None:
    record = map_field(
        FormField(
            key="permit_reference",
            label="Permit reference",
            section="References",
            type="text",
            sensitivity="business",
            required=True,
        ),
        [
            AvailableFact(
                key="permit_reference",
                value="Maybe-123",
                source="document:note",
                confidence=0.4,
                sensitivity="business",
            )
        ],
    )

    assert record.status == "user_required"
    assert record.proposed_value is None


def test_human_only_field_is_never_filled_even_with_exact_fact() -> None:
    record = map_field(
        FormField(
            key="legal_attestation",
            label="Legal attestation",
            section="Review",
            type="checkbox",
            sensitivity="confidential",
            required=True,
            human_only=True,
        ),
        [
            AvailableFact(
                key="legal_attestation",
                value="yes",
                source="profile:legal_attestation",
                confidence=1,
                sensitivity="confidential",
            )
        ],
    )

    assert record.status == "user_required"
    assert record.proposed_value is None
    assert record.sources == []


def test_retrieved_field_is_not_typed_by_agent() -> None:
    record = map_field(
        FormField(
            key="registry_value",
            label="Registry value",
            section="General",
            type="text",
            sensitivity="public",
            required=True,
            human_only=False,
            provenance="retrieved",
        ),
        [
            AvailableFact(
                key="registry_value",
                value="Known value",
                source="profile:registry_value",
                confidence=1,
                sensitivity="public",
            )
        ],
    )

    assert record.status == "left_blank"
    assert record.proposed_value is None
    assert "portal-retrieved" in record.reason


def test_sensitive_field_requires_review_and_no_proposed_fill() -> None:
    record = map_field(
        FormField(
            key="owner_identifier",
            label="Owner identifier",
            section="People",
            type="text",
            sensitivity="personal",
            required=True,
        ),
        [
            AvailableFact(
                key="owner_identifier",
                value="ID-777",
                source="profile:owner_identifier",
                confidence=1,
                sensitivity="personal",
            )
        ],
    )

    assert record.status == "needs_review"
    assert record.proposed_value is None
    assert record.confidence == 1


def test_build_facts_and_map_fields_from_generic_inputs() -> None:
    facts = build_facts(
        attributes=[
            {
                "key": "operating_address",
                "label": "Operating address",
                "value": "12 Harbor Lane",
                "sensitivity": "business",
            }
        ],
        extracted_facts=[
            {
                "key": "contact_email",
                "value": "hello@example.test",
                "source": "document:summary",
                "confidence": 0.72,
                "sensitivity": "business",
            }
        ],
    )
    records = map_fields(
        [
            FormField("operating_address", "Operating address", "General", "text", "business", True),
            FormField("contact_email", "Contact email", "General", "text", "business", True),
            FormField("unknown_required", "Unknown required", "General", "text", "business", True),
        ],
        facts,
    )

    assert [record.status for record in records] == ["filled", "needs_review", "user_required"]


def test_conditional_fields_are_generic_not_applicable_when_parent_value_differs() -> None:
    records = map_fields(
        [
            FormField("applicant_kind", "Applicant kind", "General", "radio", "business", True),
            FormField(
                "corporate_identifier",
                "Corporate identifier",
                "General",
                "text",
                "business",
                True,
                False,
                "agent_fillable",
                "applicant_kind=Corporate",
            ),
        ],
        [AvailableFact("applicant_kind", "Individual", "profile:applicant_kind", 1, "business")],
    )

    assert records[0].status == "filled"
    assert records[1].status == "not_applicable"
