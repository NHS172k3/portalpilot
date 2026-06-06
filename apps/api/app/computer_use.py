import asyncio
import base64
import queue
import threading
import time
from typing import Any
from uuid import UUID, uuid4

from openai import OpenAI
from playwright.sync_api import sync_playwright

from app.browser_executor import SafeSyncBrowserExecutor
from app.config import Settings
from app.guardrails import classify_human_only
from app.models import (
    ActivityEvent,
    AgentRequestDraft,
    ChecklistItem,
    ComputerUseAccessSessionResponse,
    ComputerUseRunRequest,
    ComputerUseRunResponse,
    ComputerUseStep,
    FieldConfidenceRecord,
    FieldStatus,
    OfficialSource,
    RegulatoryRecommendation,
    RequestType,
    Sensitivity,
    SourceType,
)


class ComputerUseHarness:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.executor = SafeSyncBrowserExecutor()

    async def run(self, request: ComputerUseRunRequest) -> ComputerUseRunResponse:
        return await asyncio.to_thread(self._run_sync, request)

    async def start_access_session(self, request: ComputerUseRunRequest, filing_id: UUID | None = None) -> ComputerUseAccessSessionResponse:
        return await access_sessions.start(self, request, filing_id=filing_id)

    async def resume_access_session(self, session_id: str, request: ComputerUseRunRequest, filing_id: UUID | None = None) -> ComputerUseRunResponse:
        return await access_sessions.resume(session_id, request, filing_id=filing_id)

    async def close_access_session(self, session_id: str, filing_id: UUID | None = None) -> bool:
        return await access_sessions.close(session_id, filing_id=filing_id)

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
        user_handoff_used = False
        user_handoff_timed_out = False
        recommendation: RegulatoryRecommendation | None = None
        checklist: list[ChecklistItem] = []
        fields: list[FieldConfidenceRecord] = []

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=not request.allow_user_handoff)
                context = browser.new_context(viewport={"width": 1024, "height": 768}, storage_state=None)
                page = context.new_page()
                page.goto(request.target_url, wait_until="domcontentloaded", timeout=self.settings.computer_use_navigation_timeout_ms)

                current_url = page.url
                page_handoff = self.executor.page_handoff_reason(page)
                if page_handoff:
                    if request.allow_user_handoff:
                        user_handoff_used = True
                        activity.append(
                            ActivityEvent(
                                event_type="user_handoff_started",
                                summary="Visible browser handed to user",
                                detail="Complete login, CAPTCHA, MFA, or authorization in the Chromium window. Do not submit, pay, endorse, or accept legal declarations.",
                            )
                        )
                        cleared = self._wait_for_user_handoff(page, request.handoff_timeout_seconds)
                        steps.append(
                            ComputerUseStep(
                                step=0,
                                action_type="user_handoff",
                                status="completed" if cleared else "blocked",
                                summary="User authorization handoff completed" if cleared else "User authorization handoff timed out",
                                blocked_reason=None if cleared else page_handoff,
                                current_url=page.url,
                            )
                        )
                        if cleared:
                            current_url = page.url
                            page_handoff = None
                        else:
                            user_handoff_timed_out = True
                    if not page_handoff:
                        pass
                    else:
                        agent_request = self._handoff(current_url, page_handoff, assisted=request.allow_user_handoff)
                        recommendation = self._blocked_page_recommendation(page, current_url, page_handoff)
                        browser.close()
                        return self._blocked_response(
                            request,
                            current_url,
                            activity,
                            steps,
                            page_handoff,
                            agent_request,
                            recommendation=recommendation,
                            checklist=[],
                            fields=[],
                            user_handoff_used=user_handoff_used,
                            user_handoff_timed_out=user_handoff_timed_out,
                        )

                recommendation, checklist, fields = self._observed_artifacts(page, current_url)

                if not self.client:
                    return self._missing_client_response(
                        request,
                        page.url,
                        activity,
                        steps,
                        recommendation=recommendation,
                        checklist=checklist,
                        fields=fields,
                        user_handoff_used=user_handoff_used,
                        user_handoff_timed_out=user_handoff_timed_out,
                    )

                run_result = self._drive_page(
                    page,
                    request,
                    activity,
                    steps,
                    assisted=request.allow_user_handoff,
                    user_handoff_used=user_handoff_used,
                    user_handoff_timed_out=user_handoff_timed_out,
                )
                run_result.recommendation = run_result.recommendation or self._observed_artifacts(page, page.url)[0]
                if not run_result.checklist and not run_result.fields:
                    _, run_result.checklist, run_result.fields = self._observed_artifacts(page, page.url)
                browser.close()
                return run_result
        except Exception as exc:
            reason = f"Computer-use run could not complete: {exc}"
            return self._blocked_response(
                request,
                request.target_url,
                activity,
                steps,
                reason,
                self._handoff(request.target_url, reason, assisted=request.allow_user_handoff),
                recommendation=recommendation,
                checklist=checklist,
                fields=fields,
                user_handoff_used=user_handoff_used,
                user_handoff_timed_out=user_handoff_timed_out,
            )

    def _wait_for_user_handoff(self, page, timeout_seconds: int) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            page.wait_for_timeout(2000)
            if not self.executor.page_handoff_reason(page):
                return True
        return False

    def _missing_client_response(
        self,
        request: ComputerUseRunRequest,
        current_url: str,
        activity: list[ActivityEvent],
        steps: list[ComputerUseStep],
        recommendation: RegulatoryRecommendation | None = None,
        checklist: list[ChecklistItem] | None = None,
        fields: list[FieldConfidenceRecord] | None = None,
        user_handoff_used: bool = False,
        user_handoff_timed_out: bool = False,
    ) -> ComputerUseRunResponse:
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
        return self._blocked_response(
            request,
            current_url,
            activity,
            steps,
            reason,
            self._handoff(current_url, reason, assisted=request.allow_user_handoff),
            recommendation=recommendation,
            checklist=checklist or [],
            fields=fields or [],
            extra_requests=self._observed_field_requests(fields or [], current_url),
            user_handoff_used=user_handoff_used,
            user_handoff_timed_out=user_handoff_timed_out,
        )

    def _drive_page(
        self,
        page,
        request: ComputerUseRunRequest,
        activity: list[ActivityEvent],
        steps: list[ComputerUseStep],
        assisted: bool,
        user_handoff_used: bool = False,
        user_handoff_timed_out: bool = False,
    ) -> ComputerUseRunResponse:
        if not self.client:
            return self._missing_client_response(
                request,
                page.url,
                activity,
                steps,
                user_handoff_used=user_handoff_used,
                user_handoff_timed_out=user_handoff_timed_out,
            )

        agent_request: AgentRequestDraft | None = None
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
                agent_request = self._handoff(page.url, reason, assisted=assisted)
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
                agent_request = self._handoff(page.url, blocked, assisted=assisted)
                break
            response = self._followup_response(page, response, computer_call)

        if agent_request:
            recommendation = self._blocked_page_recommendation(page, page.url, agent_request.why_needed)
            return self._blocked_response(
                request,
                page.url,
                activity,
                steps,
                agent_request.why_needed,
                agent_request,
                recommendation=recommendation,
                checklist=[],
                fields=[],
                user_handoff_used=user_handoff_used,
                user_handoff_timed_out=user_handoff_timed_out,
            )

        recommendation, checklist, fields = self._observed_artifacts(page, page.url)
        return ComputerUseRunResponse(
            status="completed" if steps else "observed",
            mode="openai_computer_use",
            target_url=request.target_url,
            current_url=page.url,
            recommendation=recommendation,
            checklist=checklist,
            fields=fields,
            steps=steps,
            requests=self._observed_field_requests(fields, page.url),
            activity=activity,
            agents=["portalpilot-orchestrator", "computer-use-preview"],
            user_handoff_used=user_handoff_used,
            user_handoff_timed_out=user_handoff_timed_out,
        )

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
        recommendation: RegulatoryRecommendation | None = None,
        checklist: list[ChecklistItem] | None = None,
        fields: list[FieldConfidenceRecord] | None = None,
        extra_requests: list[AgentRequestDraft] | None = None,
        user_handoff_used: bool = False,
        user_handoff_timed_out: bool = False,
    ) -> ComputerUseRunResponse:
        activity.append(ActivityEvent(event_type="human_wall_detected", summary="Browser run paused", detail=reason))
        return ComputerUseRunResponse(
            status="blocked",
            mode="openai_computer_use" if self.client else "playwright_observe_only",
            target_url=request.target_url,
            current_url=current_url,
            recommendation=recommendation,
            checklist=checklist or [],
            fields=fields or [],
            steps=steps,
            requests=[agent_request] + (extra_requests or []),
            activity=activity,
            blocked_reason=reason,
            agents=["portalpilot-orchestrator", "computer-use-preview"],
            user_handoff_used=user_handoff_used,
            user_handoff_timed_out=user_handoff_timed_out,
        )

    def _handoff(self, url: str, reason: str, assisted: bool = False) -> AgentRequestDraft:
        classified = classify_human_only(reason)
        if classified:
            classified.portal_url = url
            if assisted:
                classified.title = "Complete access in the visible browser"
                classified.prompt = (
                    "Use the Chromium window that PortalPilot opened. Complete login, CAPTCHA, MFA, or authorization yourself. "
                    "Stop before any declaration, endorsement, payment, or final submission. Leave the browser on the next safe form page so the agent can resume."
                )
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

    def _observed_artifacts(self, page, current_url: str) -> tuple[RegulatoryRecommendation, list[ChecklistItem], list[FieldConfidenceRecord]]:
        snapshot = self._page_snapshot(page)
        title = snapshot["heading"] or snapshot["title"] or "Observed portal page"
        controls = snapshot["controls"]
        fields = [
            FieldConfidenceRecord(
                portal_section="Observed form",
                field_label=label,
                proposed_value=None,
                source_type=SourceType.AGENT_INFERENCE,
                confidence=1,
                sensitivity=self._sensitivity_for_label(label),
                status=FieldStatus.USER_REQUIRED,
                reason="This field was visible in the browser page observed by the computer-use agent.",
            )
            for label in controls
        ]
        checklist = [
            ChecklistItem(
                label="Browser page observed",
                status=FieldStatus.FILLED,
                reason=f"The browser-use agent observed {len(controls)} visible fillable control(s) on the current page.",
            )
        ]
        if controls:
            checklist.append(
                ChecklistItem(
                    label="Collect values for visible fields",
                    status=FieldStatus.USER_REQUIRED,
                    reason="PortalPilot asks only for values tied to fields observed in the current browser page.",
                )
            )
        else:
            checklist.append(
                ChecklistItem(
                    label="No fillable fields observed",
                    status=FieldStatus.NEEDS_REVIEW,
                    reason="The current page may be an access, review, or informational page rather than a fillable form section.",
                )
            )
        return (
            RegulatoryRecommendation(
                filing_name=title[:120],
                jurisdiction="Observed from browser page",
                agency=snapshot["origin"] or "Observed portal",
                reason="Generated after the browser-use agent observed the live page. It does not rely on pre-browser guessed form fields.",
                prerequisites=[],
                fee_expectation=None,
                deadline=None,
                warnings=[],
                confidence=0.8 if controls else 0.55,
                sources=[
                    OfficialSource(
                        title="Observed browser page",
                        url=current_url,
                        summary=(snapshot["body_excerpt"] or title)[:240],
                    )
                ],
            ),
            checklist,
            fields,
        )

    def _blocked_page_recommendation(self, page, current_url: str, reason: str) -> RegulatoryRecommendation:
        snapshot = self._page_snapshot(page)
        title = snapshot["heading"] or snapshot["title"] or "Human-only portal step"
        return RegulatoryRecommendation(
            filing_name=title[:120],
            jurisdiction="Observed from browser page",
            agency=snapshot["origin"] or "Observed portal",
            reason=(
                "PortalPilot paused on this page because it appears to require user-only access, "
                "authorization, declaration, endorsement, submission, or payment handling."
            ),
            prerequisites=[],
            fee_expectation=None,
            deadline=None,
            warnings=[reason],
            confidence=0.75,
            sources=[
                OfficialSource(
                    title="Observed blocked browser page",
                    url=current_url,
                    summary=reason[:240],
                )
            ],
        )

    def _observed_field_requests(self, fields: list[FieldConfidenceRecord], current_url: str) -> list[AgentRequestDraft]:
        requests: list[AgentRequestDraft] = []
        for field in fields[:8]:
            if field.sensitivity == Sensitivity.CONFIDENTIAL:
                continue
            requests.append(
                AgentRequestDraft(
                    request_type=RequestType.DATA_REQUEST,
                    title=f"Provide {field.field_label}",
                    prompt=f"What value should PortalPilot use for the visible field \"{field.field_label}\"?",
                    why_needed="This question was generated only after the browser-use agent observed the field on the current page.",
                    confidence=1,
                    source_type=SourceType.AGENT_INFERENCE,
                    portal_url=current_url,
                )
            )
        return requests

    def _page_snapshot(self, page) -> dict[str, Any]:
        try:
            return page.evaluate(
                """() => {
                    const textFor = (el) => {
                        const id = el.getAttribute("id");
                        const labelled = el.getAttribute("aria-label") || el.getAttribute("placeholder") || el.getAttribute("name") || "";
                        const label = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
                        const wrapped = el.closest("label");
                        return (label?.innerText || wrapped?.innerText || labelled || el.textContent || "").trim();
                    };
                    const controls = Array.from(document.querySelectorAll("input, textarea, select"))
                        .filter((el) => {
                            const style = window.getComputedStyle(el);
                            const type = (el.getAttribute("type") || "").toLowerCase();
                            return style.visibility !== "hidden" && style.display !== "none" && type !== "hidden";
                        })
                        .map(textFor)
                        .filter(Boolean)
                        .slice(0, 20);
                    const heading = document.querySelector("h1,h2")?.innerText?.trim() || "";
                    return {
                        title: document.title || "",
                        heading,
                        origin: location.origin,
                        controls: [...new Set(controls)],
                        body_excerpt: (document.body?.innerText || "").replace(/\\s+/g, " ").trim().slice(0, 500)
                    };
                }"""
            )
        except Exception:
            return {"title": "", "heading": "", "origin": "", "controls": [], "body_excerpt": ""}

    def _sensitivity_for_label(self, label: str) -> Sensitivity:
        lowered = label.lower()
        if any(marker in lowered for marker in ["password", "otp", "mfa", "captcha", "passport", "identity", "id number", "nric"]):
            return Sensitivity.CONFIDENTIAL
        if any(marker in lowered for marker in ["email", "phone", "name", "address"]):
            return Sensitivity.PERSONAL
        return Sensitivity.BUSINESS

    def _is_access_wall(self, reason: str) -> bool:
        lowered = reason.lower()
        return any(marker in lowered for marker in ["credential", "captcha", "mfa", "otp", "log in", "login", "sign in", "authorization", "authenticate"])

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


class _AccessSession:
    def __init__(self, session_id: str, harness: ComputerUseHarness, request: ComputerUseRunRequest, filing_id: UUID | None = None):
        self.session_id = session_id
        self.harness = harness
        self.request = request
        self.filing_id = filing_id
        self.commands: queue.Queue[tuple[str, ComputerUseRunRequest | None]] = queue.Queue()
        self.results: queue.Queue[Any] = queue.Queue()
        self.ready: queue.Queue[ComputerUseAccessSessionResponse] = queue.Queue(maxsize=1)
        self.thread = threading.Thread(target=self._run, name=f"portalpilot-cua-{session_id}", daemon=True)

    def start(self) -> ComputerUseAccessSessionResponse:
        self.thread.start()
        return self.ready.get(timeout=max(60, int(self.harness.settings.computer_use_navigation_timeout_ms / 1000) + 15))

    def resume(self, request: ComputerUseRunRequest) -> ComputerUseRunResponse:
        self.commands.put(("resume", request))
        return self.results.get(timeout=max(45, request.handoff_timeout_seconds + 45))

    def close(self) -> None:
        self.commands.put(("close", None))

    def _run(self) -> None:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=False)
                context = browser.new_context(viewport={"width": 1024, "height": 768}, storage_state=None)
                page = context.new_page()
                page.goto(
                    self.request.target_url,
                    wait_until="domcontentloaded",
                    timeout=self.harness.settings.computer_use_navigation_timeout_ms,
                )
                handoff_reason = self.harness.executor.page_handoff_reason(page)
                self.ready.put(
                    ComputerUseAccessSessionResponse(
                        session_id=self.session_id,
                        status="waiting_for_user" if handoff_reason else "ready_to_resume",
                        target_url=self.request.target_url,
                        current_url=page.url,
                        handoff_reason=handoff_reason,
                        prompt=(
                            "Complete login, CAPTCHA, MFA, or authorization in the visible Chromium window. "
                            "Do not submit, pay, endorse, or accept legal declarations. Click Resume in PortalPilot when the safe form page is visible."
                        ),
                    )
                )
                while True:
                    command, payload = self.commands.get()
                    if command == "close":
                        browser.close()
                        return
                    if command != "resume" or payload is None:
                        continue

                    handoff_reason = self.harness.executor.page_handoff_reason(page)
                    activity = [
                        ActivityEvent(
                            event_type="user_handoff_resume_requested",
                            summary="User requested browser-agent resume",
                            detail="PortalPilot checked whether the visible browser had cleared the access wall.",
                        )
                    ]
                    steps: list[ComputerUseStep] = [
                        ComputerUseStep(
                            step=0,
                            action_type="user_handoff",
                            status="completed" if not handoff_reason else "blocked",
                            summary="User access handoff cleared" if not handoff_reason else "Access handoff is still active",
                            blocked_reason=handoff_reason,
                            current_url=page.url,
                        )
                    ]
                    if handoff_reason:
                        recommendation = self.harness._blocked_page_recommendation(page, page.url, handoff_reason)
                        self.results.put(
                            self.harness._blocked_response(
                                payload,
                                page.url,
                                activity,
                                steps,
                                handoff_reason,
                                self.harness._handoff(page.url, handoff_reason, assisted=True),
                                recommendation=recommendation,
                                checklist=[],
                                fields=[],
                                user_handoff_used=True,
                            )
                        )
                        continue

                    result = self.harness._drive_page(
                        page,
                        payload,
                        activity,
                        steps,
                        assisted=True,
                        user_handoff_used=True,
                    )
                    self.results.put(result)
                    browser.close()
                    return
        except Exception as exc:
            reason = f"Access session failed: {exc}"
            self.ready.put(
                ComputerUseAccessSessionResponse(
                    session_id=self.session_id,
                    status="failed",
                    target_url=self.request.target_url,
                    current_url=self.request.target_url,
                    handoff_reason=reason,
                    prompt=reason,
                )
            )


class AccessSessionManager:
    def __init__(self):
        self.sessions: dict[str, _AccessSession] = {}

    async def start(
        self,
        harness: ComputerUseHarness,
        request: ComputerUseRunRequest,
        filing_id: UUID | None = None,
    ) -> ComputerUseAccessSessionResponse:
        session_id = str(uuid4())
        session = _AccessSession(session_id, harness, request, filing_id=filing_id)
        self.sessions[session_id] = session
        try:
            response = await asyncio.to_thread(session.start)
        except Exception:
            self.sessions.pop(session_id, None)
            raise
        if response.status == "failed":
            self.sessions.pop(session_id, None)
        return response

    async def resume(
        self,
        session_id: str,
        request: ComputerUseRunRequest,
        filing_id: UUID | None = None,
    ) -> ComputerUseRunResponse:
        session = self.sessions.get(session_id)
        if not session:
            return ComputerUseRunResponse(
                status="blocked",
                mode="access_session",
                target_url=request.target_url,
                current_url=request.target_url,
                blocked_reason="Access session was not found or has already ended.",
            )
        if filing_id is not None and session.filing_id is not None and session.filing_id != filing_id:
            return ComputerUseRunResponse(
                status="blocked",
                mode="access_session",
                target_url=request.target_url,
                current_url=request.target_url,
                blocked_reason="Access session belongs to a different filing.",
            )
        result = await asyncio.to_thread(session.resume, request)
        still_waiting_for_user = result.status == "blocked" and result.user_handoff_used and not result.user_handoff_timed_out
        if not still_waiting_for_user:
            self.sessions.pop(session_id, None)
        return result

    async def close(self, session_id: str, filing_id: UUID | None = None) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        if filing_id is not None and session.filing_id is not None and session.filing_id != filing_id:
            return False
        self.sessions.pop(session_id, None)
        await asyncio.to_thread(session.close)
        return True


access_sessions = AccessSessionManager()
