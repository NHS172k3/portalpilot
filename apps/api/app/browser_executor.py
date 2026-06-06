import asyncio
import re
import time
from typing import Any

from playwright.async_api import Page
from playwright.sync_api import Page as SyncPage

from app.guardrails import classify_human_only

ACCESS_MARKERS = (
    r"\blog\s*in\b",
    r"\blogin\b",
    r"\bsign\s*in\b",
    r"\bpassword\b",
    r"\bcaptcha\b",
    r"\bmfa\b",
    r"\botp\b",
    r"\bone[-\s]?time\b",
    r"\bauthenticate\b",
    r"\bauthentication\b",
    r"\bauthorization\b",
    r"\bauthorisation\b",
    r"\bverification\s+code\b",
    r"\bsecurity\s+code\b",
    r"\bchallenge\b",
)

PAGE_HUMAN_ONLY_MARKERS = (
    r"\bi\s+agree\b",
    r"\bterms\s+and\s+conditions\b",
    r"\bcertif(y|ication|ies)\b",
    r"\bdeclaration\b",
    r"\bstatutory\b",
    r"\bendorse(ment|d|s)?\b",
    r"\bfinal[-\s]?submit\b",
    r"\bconfirm[-\s]?submission\b",
    r"\bcontinue\s+to\s+payment\b",
    r"\bproceed\s+to\s+payment\b",
    r"\bmake\s+payment\b",
    r"\bfee\s+payment\b",
)


def _action_value(action: Any, name: str, default: Any = None) -> Any:
    if isinstance(action, dict):
        return action.get(name, default)
    return getattr(action, name, default)


class SafeBrowserExecutor:
    async def page_handoff_reason(self, page: Page) -> str | None:
        risky = await page.locator(
            "input[type='password'], input[name*='otp' i], input[name*='mfa' i], input[name*='captcha' i], input[name*='verification' i], input[name*='challenge' i], input[autocomplete='one-time-code' i], input[id*='captcha' i], input[id*='verification' i], img[alt*='captcha' i]"
        ).count()
        if risky:
            return "Credential, CAPTCHA, MFA, or one-time-code input detected on the portal page."
        if _has_access_marker(await self._access_control_text(page)):
            return "Login, CAPTCHA, MFA, OTP, or authorization step detected on the portal page."
        if _has_page_human_only_marker(await self._human_only_page_text(page)):
            return "Declaration, endorsement, final submission, or payment step detected on the portal page."
        return None

    async def execute(self, page: Page, action: Any) -> tuple[str, str | None]:
        action_type = str(_action_value(action, "type", "unknown"))
        summary = self._describe_action(action)
        blocked = await self._blocked_reason(page, action)
        if blocked:
            return f"blocked: {summary}", blocked

        if action_type == "click":
            await page.mouse.click(
                int(_action_value(action, "x", 0)),
                int(_action_value(action, "y", 0)),
                button=str(_action_value(action, "button", "left")),
            )
        elif action_type == "double_click":
            await page.mouse.dblclick(int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
        elif action_type == "scroll":
            await page.mouse.move(int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
            await page.evaluate(
                "(offset) => window.scrollBy(offset.x, offset.y)",
                {"x": int(_action_value(action, "scroll_x", 0)), "y": int(_action_value(action, "scroll_y", 0))},
            )
        elif action_type == "keypress":
            for key in _action_value(action, "keys", []) or []:
                await page.keyboard.press(" " if str(key).lower() == "space" else str(key))
        elif action_type == "type":
            await page.keyboard.type(str(_action_value(action, "text", "")))
        elif action_type == "wait":
            await asyncio.sleep(1)
        elif action_type == "screenshot":
            pass
        else:
            return f"blocked: {summary}", f"Unsupported computer action type: {action_type}"

        await page.wait_for_timeout(350)
        return summary, None

    async def _blocked_reason(self, page: Page, action: Any) -> str | None:
        page_reason = await self.page_handoff_reason(page)
        if page_reason:
            return page_reason

        action_type = str(_action_value(action, "type", "unknown"))
        action_text = self._describe_action(action)
        if classify_human_only(action_text):
            return "Human-only action blocked by PortalPilot guardrails."

        if action_type in {"click", "double_click"}:
            element_text = await self._element_text_at(page, int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
            if classify_human_only(element_text):
                return f"Click target is human-only: {element_text[:120]}"
            selector = await self._element_selector_at(page, int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
            if selector and classify_human_only(selector):
                return f"Click target selector is human-only: {selector[:120]}"

        if action_type == "type":
            target = await page.evaluate(
                """() => {
                    const el = document.activeElement;
                    if (!el) return "";
                    return [
                        el.tagName,
                        el.getAttribute("type"),
                        el.getAttribute("name"),
                        el.getAttribute("autocomplete"),
                        el.getAttribute("aria-label"),
                        el.getAttribute("placeholder")
                    ].filter(Boolean).join(" ");
                }"""
            )
            if classify_human_only(str(target)):
                return f"Typing target is human-only: {target}"

        return None

    async def _element_text_at(self, page: Page, x: int, y: int) -> str:
        try:
            return str(
                await page.evaluate(
                    """([x, y]) => {
                        const el = document.elementFromPoint(x, y);
                        if (!el) return "";
                        return [
                            el.innerText,
                            el.textContent,
                            el.getAttribute("aria-label"),
                            el.getAttribute("title"),
                            el.getAttribute("value")
                        ].filter(Boolean).join(" ");
                    }""",
                    [x, y],
                )
            )
        except Exception:
            return ""

    async def _element_selector_at(self, page: Page, x: int, y: int) -> str:
        try:
            return str(
                await page.evaluate(
                    """([x, y]) => {
                        const el = document.elementFromPoint(x, y);
                        if (!el) return "";
                        return [
                            el.tagName,
                            el.id ? `#${el.id}` : "",
                            el.className ? `.${String(el.className).replaceAll(" ", ".")}` : "",
                            el.getAttribute("type"),
                            el.getAttribute("name"),
                            el.getAttribute("role")
                        ].filter(Boolean).join(" ");
                    }""",
                    [x, y],
                )
            )
        except Exception:
            return ""

    def _describe_action(self, action: Any) -> str:
        action_type = str(_action_value(action, "type", "unknown"))
        if action_type in {"click", "double_click"}:
            return f"{action_type} at ({_action_value(action, 'x', 0)}, {_action_value(action, 'y', 0)})"
        if action_type == "type":
            text = str(_action_value(action, "text", ""))
            return f"type {len(text)} characters"
        if action_type == "scroll":
            return f"scroll by ({_action_value(action, 'scroll_x', 0)}, {_action_value(action, 'scroll_y', 0)})"
        if action_type == "keypress":
            return f"keypress {_action_value(action, 'keys', [])}"
        return action_type

    async def _access_control_text(self, page: Page) -> str:
        try:
            return str(
                await page.locator(
                    "form, button, input, label, [role='dialog'], [aria-modal='true'], [id*='login' i], [class*='login' i]"
                ).evaluate_all(
                    """elements => elements.map(el => [
                        el.innerText,
                        el.textContent,
                        el.getAttribute('aria-label'),
                        el.getAttribute('placeholder'),
                        el.getAttribute('name'),
                        el.getAttribute('id'),
                        el.getAttribute('value')
                    ].filter(Boolean).join(' ')).join('\\n')"""
                )
            )
        except Exception:
            return ""

    async def _human_only_page_text(self, page: Page) -> str:
        try:
            return str(
                await page.locator("form, button, input, label, [role='dialog'], [aria-modal='true'], main").evaluate_all(
                    """elements => elements.map(el => [
                        el.innerText,
                        el.textContent,
                        el.getAttribute('aria-label'),
                        el.getAttribute('placeholder'),
                        el.getAttribute('name'),
                        el.getAttribute('id'),
                        el.getAttribute('value')
                    ].filter(Boolean).join(' ')).join('\\n')"""
                )
            )
        except Exception:
            return ""


class SafeSyncBrowserExecutor:
    def page_handoff_reason(self, page: SyncPage) -> str | None:
        risky = page.locator(
            "input[type='password'], input[name*='otp' i], input[name*='mfa' i], input[name*='captcha' i], input[name*='verification' i], input[name*='challenge' i], input[autocomplete='one-time-code' i], input[id*='captcha' i], input[id*='verification' i], img[alt*='captcha' i]"
        ).count()
        if risky:
            return "Credential, CAPTCHA, MFA, or one-time-code input detected on the portal page."
        if _has_access_marker(self._access_control_text(page)):
            return "Login, CAPTCHA, MFA, OTP, or authorization step detected on the portal page."
        if _has_page_human_only_marker(self._human_only_page_text(page)):
            return "Declaration, endorsement, final submission, or payment step detected on the portal page."
        return None

    def execute(self, page: SyncPage, action: Any) -> tuple[str, str | None]:
        action_type = str(_action_value(action, "type", "unknown"))
        summary = self._describe_action(action)
        blocked = self._blocked_reason(page, action)
        if blocked:
            return f"blocked: {summary}", blocked

        if action_type == "click":
            page.mouse.click(
                int(_action_value(action, "x", 0)),
                int(_action_value(action, "y", 0)),
                button=str(_action_value(action, "button", "left")),
            )
        elif action_type == "double_click":
            page.mouse.dblclick(int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
        elif action_type == "scroll":
            page.mouse.move(int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
            page.evaluate(
                "(offset) => window.scrollBy(offset.x, offset.y)",
                {"x": int(_action_value(action, "scroll_x", 0)), "y": int(_action_value(action, "scroll_y", 0))},
            )
        elif action_type == "keypress":
            for key in _action_value(action, "keys", []) or []:
                page.keyboard.press(" " if str(key).lower() == "space" else str(key))
        elif action_type == "type":
            page.keyboard.type(str(_action_value(action, "text", "")))
        elif action_type == "wait":
            time.sleep(1)
        elif action_type == "screenshot":
            pass
        else:
            return f"blocked: {summary}", f"Unsupported computer action type: {action_type}"

        page.wait_for_timeout(350)
        return summary, None

    def _blocked_reason(self, page: SyncPage, action: Any) -> str | None:
        page_reason = self.page_handoff_reason(page)
        if page_reason:
            return page_reason

        action_type = str(_action_value(action, "type", "unknown"))
        action_text = self._describe_action(action)
        if classify_human_only(action_text):
            return "Human-only action blocked by PortalPilot guardrails."

        if action_type in {"click", "double_click"}:
            element_text = self._element_text_at(page, int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
            if classify_human_only(element_text):
                return f"Click target is human-only: {element_text[:120]}"
            selector = self._element_selector_at(page, int(_action_value(action, "x", 0)), int(_action_value(action, "y", 0)))
            if selector and classify_human_only(selector):
                return f"Click target selector is human-only: {selector[:120]}"

        if action_type == "type":
            target = page.evaluate(
                """() => {
                    const el = document.activeElement;
                    if (!el) return "";
                    return [
                        el.tagName,
                        el.getAttribute("type"),
                        el.getAttribute("name"),
                        el.getAttribute("autocomplete"),
                        el.getAttribute("aria-label"),
                        el.getAttribute("placeholder")
                    ].filter(Boolean).join(" ");
                }"""
            )
            if classify_human_only(str(target)):
                return f"Typing target is human-only: {target}"

        return None

    def _element_text_at(self, page: SyncPage, x: int, y: int) -> str:
        try:
            return str(
                page.evaluate(
                    """([x, y]) => {
                        const el = document.elementFromPoint(x, y);
                        if (!el) return "";
                        return [
                            el.innerText,
                            el.textContent,
                            el.getAttribute("aria-label"),
                            el.getAttribute("title"),
                            el.getAttribute("value")
                        ].filter(Boolean).join(" ");
                    }""",
                    [x, y],
                )
            )
        except Exception:
            return ""

    def _element_selector_at(self, page: SyncPage, x: int, y: int) -> str:
        try:
            return str(
                page.evaluate(
                    """([x, y]) => {
                        const el = document.elementFromPoint(x, y);
                        if (!el) return "";
                        return [
                            el.tagName,
                            el.id ? `#${el.id}` : "",
                            el.className ? `.${String(el.className).replaceAll(" ", ".")}` : "",
                            el.getAttribute("type"),
                            el.getAttribute("name"),
                            el.getAttribute("role")
                        ].filter(Boolean).join(" ");
                    }""",
                    [x, y],
                )
            )
        except Exception:
            return ""

    def _describe_action(self, action: Any) -> str:
        action_type = str(_action_value(action, "type", "unknown"))
        if action_type in {"click", "double_click"}:
            return f"{action_type} at ({_action_value(action, 'x', 0)}, {_action_value(action, 'y', 0)})"
        if action_type == "type":
            text = str(_action_value(action, "text", ""))
            return f"type {len(text)} characters"
        if action_type == "scroll":
            return f"scroll by ({_action_value(action, 'scroll_x', 0)}, {_action_value(action, 'scroll_y', 0)})"
        if action_type == "keypress":
            return f"keypress {_action_value(action, 'keys', [])}"
        return action_type

    def _access_control_text(self, page: SyncPage) -> str:
        try:
            return str(
                page.locator(
                    "form, button, input, label, [role='dialog'], [aria-modal='true'], [id*='login' i], [class*='login' i]"
                ).evaluate_all(
                    """elements => elements.map(el => [
                        el.innerText,
                        el.textContent,
                        el.getAttribute('aria-label'),
                        el.getAttribute('placeholder'),
                        el.getAttribute('name'),
                        el.getAttribute('id'),
                        el.getAttribute('value')
                    ].filter(Boolean).join(' ')).join('\\n')"""
                )
            )
        except Exception:
            return ""

    def _human_only_page_text(self, page: SyncPage) -> str:
        try:
            return str(
                page.locator("form, button, input, label, [role='dialog'], [aria-modal='true'], main").evaluate_all(
                    """elements => elements.map(el => [
                        el.innerText,
                        el.textContent,
                        el.getAttribute('aria-label'),
                        el.getAttribute('placeholder'),
                        el.getAttribute('name'),
                        el.getAttribute('id'),
                        el.getAttribute('value')
                    ].filter(Boolean).join(' ')).join('\\n')"""
                )
            )
        except Exception:
            return ""


def _has_access_marker(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(marker, lowered) for marker in ACCESS_MARKERS)


def _has_page_human_only_marker(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(marker, lowered) for marker in PAGE_HUMAN_ONLY_MARKERS)
