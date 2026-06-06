import pytest

from app.guardrails import assert_agent_action_allowed, classify_human_only
from app.models import RequestType


@pytest.mark.parametrize(
    "action",
    [
        "Log in with the company credentials",
        "Confirm portal access before filling the application",
        "Complete account access on the official portal",
        "Solve the CAPTCHA challenge",
        "Approve MFA with the OTP",
        "Check the statutory declaration box",
        "Endorse the filing on behalf of the director",
        "Click final submit",
        "Proceed to payment and pay the filing fee",
    ],
)
def test_human_only_actions_become_handoffs(action):
    request = classify_human_only(action)

    assert request is not None
    assert request.request_type == RequestType.HUMAN_WALL_HANDOFF
    assert "never performs" in request.why_needed


def test_safe_draft_action_is_allowed():
    assert classify_human_only("Save draft and continue to the next non-final section") is None
    assert_agent_action_allowed("Save draft and continue to the next non-final section")


def test_human_only_action_executor_blocks():
    with pytest.raises(ValueError, match="Human-only action blocked"):
        assert_agent_action_allowed("Click submit and pay")
