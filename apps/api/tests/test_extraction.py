from app.extraction import extract_facts, normalize_key


def test_extracts_key_value_facts() -> None:
    facts = extract_facts("Trading name: North Pier Studio\nAnnual turnover = 120000\n")

    assert [fact.key for fact in facts] == ["trading_name", "annual_turnover"]
    assert facts[0].value == "North Pier Studio"
    assert facts[0].confidence > 0.5


def test_extracts_summary_when_no_pairs() -> None:
    facts = extract_facts("A short unstructured note about the business.")

    assert len(facts) == 1
    assert facts[0].key == "document_summary"
    assert facts[0].confidence < 0.5


def test_normalize_key_is_generic() -> None:
    assert normalize_key("Operating Address / Unit") == "operating_address_unit"
