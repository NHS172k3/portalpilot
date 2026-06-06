import re

from app.models import AgentRequestDraft, RequestType

HUMAN_ONLY_PATTERNS = (
    r"\blog\s*in\b",
    r"\blogin\b",
    r"\bsign\s*in\b",
    r"\baccount\s+access\b",
    r"\bportal\s+access\b",
    r"\bauthenticate\b",
    r"\bcredential(s)?\b",
    r"\bpassword\b",
    r"\bcaptcha\b",
    r"\bmfa\b",
    r"\botp\b",
    r"\bauthentication\b",
    r"\bdeclaration\b",
    r"\bi\s+agree\b",
    r"\bterms\s+and\s+conditions\b",
    r"\bcertif(y|ication|ies)\b",
    r"\bstatutory\b",
    r"\bsubmit\b",
    r"\bfinal[-\s]?submit\b",
    r"\bendorse(ment|d|s)?\b",
    r"\bproceed\s+to\s+payment\b",
    r"\bcontinue\s+to\s+payment\b",
    r"\bmake\s+payment\b",
    r"\bfee\s+payment\b",
    r"\bpayment\b",
    r"\bpay\b",
    r"\bconfirm[-\s]?submission\b",
)


def classify_human_only(action_text: str) -> AgentRequestDraft | None:
    lowered = action_text.lower()
    if not any(re.search(pattern, lowered) for pattern in HUMAN_ONLY_PATTERNS):
        return None
    return AgentRequestDraft(
        request_type=RequestType.HUMAN_WALL_HANDOFF,
        title="Human-only access step reached",
        prompt=(
            "Complete login, authentication/MFA/CAPTCHA yourself if required. "
            "For declarations, endorsement, submission, or payment, proceed only if you personally intend to take that action; "
            "then return only on a safe non-final form or review page before resuming the agent."
        ),
        why_needed="PortalPilot never performs legally binding, credentialed, CAPTCHA, MFA, endorsement, submission, or payment actions.",
        confidence=1,
    )


def is_human_only_action(action_text: str) -> bool:
    return classify_human_only(action_text) is not None


def assert_agent_action_allowed(action_text: str) -> None:
    if is_human_only_action(action_text):
        raise ValueError("Human-only action blocked by PortalPilot guardrails")
