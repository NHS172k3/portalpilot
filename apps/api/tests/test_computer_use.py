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
                "controls": [
                    {"label": "Password", "kind": "password input", "section": "Sign in", "optional": False, "choices": []},
                    {"label": "Captcha", "kind": "text input", "section": "Sign in", "optional": False, "choices": []},
                ],
                "body_excerpt": "Sign in Password Captcha",
            }

    harness = ComputerUseHarness(Settings(openai_api_key="", supabase_url="", supabase_service_role_key=""))

    recommendation = harness._blocked_page_recommendation(FakePage(), FakePage.url, "Credential step detected")

    assert recommendation.filing_name == "Sign in"
    assert recommendation.warnings == ["Credential step detected"]
    assert "paused" in recommendation.reason


def test_observed_artifacts_group_choices_and_skip_optional_requests():
    class FakePage:
        url = "https://example.gov/form"

        def evaluate(self, _script):
            return {
                "title": "SFA Form",
                "heading": "Applicant Details",
                "origin": "https://example.gov",
                "controls": [
                    {"label": "Name", "kind": "text input", "section": "Applicant Details", "optional": False, "choices": []},
                    {"label": "Gender", "kind": "single-choice group", "section": "Applicant Details", "optional": False, "choices": ["Male [M]", "Female [F]"]},
                    {"label": "Designation", "kind": "text input", "section": "Applicant Details", "optional": True, "choices": []},
                    {"label": "ID No.", "kind": "text input", "section": "Applicant Details", "optional": False, "choices": []},
                ],
                "body_excerpt": "Applicant Details Name Gender Male Female Designation ID No.",
            }

    harness = ComputerUseHarness(Settings(openai_api_key="", supabase_url="", supabase_service_role_key=""))

    _, _, fields = harness._observed_artifacts(FakePage(), FakePage.url)
    requests = harness._observed_field_requests(fields, FakePage.url)

    assert [field.field_label for field in fields] == ["Name", "Gender", "Designation", "ID No."]
    assert "Choices: Male [M], Female [F]." in fields[1].reason
    assert fields[2].status == "needs_review"
    assert fields[3].sensitivity == "confidential"
    assert [request.title for request in requests] == ["Provide Name", "Provide Gender", "Provide Designation"]


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
