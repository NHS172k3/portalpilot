from app.research import _coerce_recommendation, _coerce_string_list, _is_official_source, _strip_json_fence


def test_strips_json_fence() -> None:
    assert _strip_json_fence('```json\n{"recommendations": []}\n```') == '{"recommendations": []}'


def test_coerces_recommendation_and_filters_bad_links() -> None:
    recommendation = _coerce_recommendation(
        {
            "title": "Annual filing",
            "reason": "Official register requires it.",
            "prerequisites": ["Active entity"],
            "fee": "$10",
            "timeline": "Within 30 days",
            "warnings": ["Human review required"],
            "source_links": [{"title": "Agency", "url": "https://agency.gov.sg/form"}, {"url": "not-a-url"}],
            "confidence": 1.2,
        }
    )

    assert recommendation.title == "Annual filing"
    assert recommendation.confidence == 1
    assert recommendation.source_links == [{"title": "Agency", "url": "https://agency.gov.sg/form"}]


def test_coerces_string_list_without_splitting_characters() -> None:
    assert _coerce_string_list("Prepare records") == ["Prepare records"]
    assert _coerce_string_list(["A", "B"]) == ["A", "B"]


def test_filters_to_official_source_hosts() -> None:
    assert _is_official_source("https://example.gov.sg/path")
    assert _is_official_source("https://service.gov/path")
    assert not _is_official_source("https://example.com/path")
