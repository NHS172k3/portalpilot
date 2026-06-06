from app.computer_use import AccessSessionManager, ComputerUseHarness
from app.config import Settings
from app.browser_executor import _has_page_human_only_marker
from app.models import ComputerUseRunRequest, ComputerUseRunResponse


def test_assisted_handoff_prompt_tells_user_to_use_visible_browser():
    harness = ComputerUseHarness(Settings(openai_api_key="", supabase_url="", supabase_service_role_key=""))

    request = harness._handoff("https://example.gov/login", "Complete login and CAPTCHA", assisted=True)

    assert request.title == "Complete access in the visible browser"
    assert "Chromium window" in request.prompt
    assert "CAPTCHA" in request.prompt
    assert "Stop before any declaration" in request.prompt
    assert request.portal_url == "https://example.gov/login"


def test_page_human_only_marker_detects_generic_final_steps():
    assert _has_page_human_only_marker("I agree to the declaration above")
    assert _has_page_human_only_marker("Continue to payment")
    assert _has_page_human_only_marker("Certification and final submission")
    assert not _has_page_human_only_marker("Continue to next safe form section")


def test_blocked_page_recommendation_does_not_emit_wall_fields():
    class FakePage:
        url = "https://example.gov/login"

        def evaluate(self, _script):
            return {
                "title": "Portal Login",
                "heading": "Sign in",
                "origin": "https://example.gov",
                "controls": ["Password", "Captcha"],
                "body_excerpt": "Sign in Password Captcha",
            }

    harness = ComputerUseHarness(Settings(openai_api_key="", supabase_url="", supabase_service_role_key=""))

    recommendation = harness._blocked_page_recommendation(FakePage(), FakePage.url, "Credential step detected")

    assert recommendation.filing_name == "Sign in"
    assert recommendation.warnings == ["Credential step detected"]
    assert "paused" in recommendation.reason


async def test_access_session_is_retained_when_resume_is_too_early():
    class FakeSession:
        def resume(self, _request):
            return ComputerUseRunResponse(
                status="blocked",
                mode="access_session",
                target_url="https://example.gov/login",
                current_url="https://example.gov/login",
                blocked_reason="Login still present",
                user_handoff_used=True,
                user_handoff_timed_out=False,
            )

    manager = AccessSessionManager()
    manager.sessions["session-1"] = FakeSession()

    result = await manager.resume(
        "session-1",
        ComputerUseRunRequest(target_url="https://example.gov/login", allow_user_handoff=True),
    )

    assert result.status == "blocked"
    assert "session-1" in manager.sessions


async def test_access_session_close_removes_session():
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    session = FakeSession()
    manager = AccessSessionManager()
    manager.sessions["session-1"] = session

    assert await manager.close("session-1")
    assert session.closed
    assert "session-1" not in manager.sessions
