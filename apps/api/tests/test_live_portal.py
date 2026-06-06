from app.engine.portal import _html_title


def test_extracts_html_title() -> None:
    assert _html_title("<html><title> Portal Login </title></html>") == "Portal Login"


def test_missing_html_title_returns_none() -> None:
    assert _html_title("<html></html>") is None
