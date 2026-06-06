import asyncio
import base64
from typing import Any

from openai import OpenAI
from playwright.sync_api import sync_playwright

from app.browser_executor import SafeSyncBrowserExecutor
from app.config import Settings
from app.guardrails import classify_human_only
from app.models import (
    ActivityEvent,
    AgentRequestDraft,
    ComputerUseRunRequest,
    ComputerUseRunResponse,
    ComputerUseStep,
    RequestType,
    SourceType,
)


class ComputerUseHarness:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.executor = SafeSyncBrowserExecutor()

    async def run(self, request: ComputerUseRunRequest) -> ComputerUseRunResponse:
        return await asyncio.to_thread(self._run_sync, request)

    def _run_sync(self, request: ComputerUseRunRequest) -> ComputerUseRunResponse:
        activity = [
            ActivityEvent(
                event_type="computer_use_started",
                summary="Safe browser run started",
                detail=f"Target: {request.target_url}",
            )
        ]
        steps: list[ComputerUseStep] = []
        agent_request: AgentRequestDraft | None = None

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1024, "height": 768}, storage_state=None)
                page = context.new_page()
                page.goto(request.target_url, wait_until="domcontentloaded", timeout=15000)

                current_url = page.url
                page_handoff = self.executor.page_handoff_reason(page)
                if page_handoff:
                    agent_request = self._handoff(current_url, page_handoff)
                    browser.close()
                    return self._blocked_response(request, current_url, activity, steps, page_handoff, agent_request)

                if not self.client:
                    reason = "OPENAI_API_KEY is missing; browser page opened, but CUA model actions were not requested."
                    steps.append(
                        ComputerUseStep(
                            step=0,
                            action_type="diagnostic",
                            status="blocked",
                            summary=reason,
                            blocked_reason=reason,
                            current_url=current_url,
                        )
                    )
                    browser.close()
                    return self._blocked_response(request, current_url, activity, steps, reason, self._handoff(current_url, reason))

                response = self._initial_response(page, request)
                for index in range(min(request.max_steps, self.settings.computer_use_max_steps)):
                    computer_call = self._first_computer_call(response)
                    if not computer_call:
                        activity.append(
                            ActivityEvent(
                                event_type="computer_use_completed",
                                summary="Computer-use model stopped requesting browser actions",
                                detail=self._output_text(response),
                            )
                        )
                        break

                    safety_checks = self._pending_safety_checks(computer_call)
                    if safety_checks:
                        reason = "OpenAI computer-use safety check requires human review before continuing."
                        agent_request = self._handoff(page.url, reason)
                        steps.append(
                            ComputerUseStep(
                                step=index + 1,
                                action_type="safety_check",
                                status="blocked",
                                summary=reason,
                                blocked_reason=str(safety_checks),
                                current_url=page.url,
                            )
                        )
                        break

                    action = self._action(computer_call)
                    action_type = self._action_type(action)
                    summary, blocked = self.executor.execute(page, action)
                    steps.append(
                        ComputerUseStep(
                            step=index + 1,
                            action_type=action_type,
                            status="blocked" if blocked else "executed",
                            summary=summary,
                            blocked_reason=blocked,
                            current_url=page.url,
                        )
                    )
                    if blocked:
                        agent_request = self._handoff(page.url, blocked)
                        break
                    response = self._followup_response(page, response, computer_call)

                current_url = page.url
                browser.close()

            if agent_request:
                return self._blocked_response(request, current_url, activity, steps, agent_request.why_needed, agent_request)

            status = "completed" if steps else "observed"
            return ComputerUseRunResponse(
                status=status,
                mode="openai_computer_use",
                target_url=request.target_url,
                current_url=current_url,
                steps=steps,
                activity=activity,
                agents=["portalpilot-orchestrator", "computer-use-preview"],
            )
        except Exception as exc:
            reason = f"Computer-use run could not complete: {exc}"
            return self._blocked_response(request, request.target_url, activity, steps, reason, self._handoff(request.target_url, reason))

    def _initial_response(self, page, request: ComputerUseRunRequest):
        screenshot = self._screenshot_data_url(page)
        objective = request.objective or "Prepare this official portal page by filling only safe, non-final, non-credential business fields."
        return self.client.responses.create(  # type: ignore[union-attr]
            model=self.settings.computer_use_model,
            tools=[
                {
                    "type": "computer_use_preview",
                    "display_width": 1024,
                    "display_height": 768,
                    "environment": "browser",
                }
            ],
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are PortalPilot's safe browser agent. "
                                "Only inspect and fill non-final business fields. "
                                "Do not log in, enter credentials, solve CAPTCHA/MFA/OTP, accept declarations, endorse, pay, submit, or final-submit. "
                                f"Objective: {objective}"
                            ),
                        },
                        {"type": "input_image", "image_url": screenshot},
                    ],
                }
            ],
            reasoning={"summary": "concise"},
            truncation="auto",
        )

    def _followup_response(self, page, previous_response: Any, computer_call: Any):
        return self.client.responses.create(  # type: ignore[union-attr]
            model=self.settings.computer_use_model,
            previous_response_id=previous_response.id,
            tools=[
                {
                    "type": "computer_use_preview",
                    "display_width": 1024,
                    "display_height": 768,
                    "environment": "browser",
                }
            ],
            input=[
                {
                    "type": "computer_call_output",
                    "call_id": self._value(computer_call, "call_id"),
                    "acknowledged_safety_checks": [],
                    "current_url": page.url,
                    "output": {
                        "type": "computer_screenshot",
                        "image_url": self._screenshot_data_url(page),
                    },
                }
            ],
            truncation="auto",
        )

    def _screenshot_data_url(self, page) -> str:
        screenshot = page.screenshot()
        return "data:image/png;base64," + base64.b64encode(screenshot).decode("utf-8")

    def _blocked_response(
        self,
        request: ComputerUseRunRequest,
        current_url: str,
        activity: list[ActivityEvent],
        steps: list[ComputerUseStep],
        reason: str,
        agent_request: AgentRequestDraft,
    ) -> ComputerUseRunResponse:
        activity.append(ActivityEvent(event_type="human_wall_detected", summary="Browser run paused", detail=reason))
        return ComputerUseRunResponse(
            status="blocked",
            mode="openai_computer_use" if self.client else "playwright_observe_only",
            target_url=request.target_url,
            current_url=current_url,
            steps=steps,
            requests=[agent_request],
            activity=activity,
            blocked_reason=reason,
            agents=["portalpilot-orchestrator", "computer-use-preview"],
        )

    def _handoff(self, url: str, reason: str) -> AgentRequestDraft:
        classified = classify_human_only(reason)
        if classified:
            classified.portal_url = url
            return classified
        return AgentRequestDraft(
            request_type=RequestType.HUMAN_WALL_HANDOFF,
            title="Human review required before browser run continues",
            prompt="Review the portal page yourself, complete any access or legally binding step if required, and resume only after the page is safe for non-final field preparation.",
            why_needed=reason,
            confidence=1,
            source_type=SourceType.AGENT_INFERENCE,
            portal_url=url,
        )

    def _first_computer_call(self, response: Any) -> Any | None:
        for item in getattr(response, "output", []) or []:
            if self._value(item, "type") == "computer_call":
                return item
        return None

    def _pending_safety_checks(self, computer_call: Any) -> Any:
        return self._value(computer_call, "pending_safety_checks", []) or []

    def _action(self, computer_call: Any) -> Any:
        return self._value(computer_call, "action", {})

    def _action_type(self, action: Any) -> str:
        return str(self._value(action, "type", "unknown"))

    def _output_text(self, response: Any) -> str | None:
        return getattr(response, "output_text", None)

    def _value(self, item: Any, key: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)
