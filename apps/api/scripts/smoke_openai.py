# /// script
# requires-python = ">=3.12"
# ///
"""Phase 0 OpenAI smoke checks.

This script intentionally uses raw HTTPS calls so it can verify the live
Responses API surface before the app chooses an SDK integration.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_ROOT = "https://api.openai.com/v1"


def load_env() -> None:
    for filename in (".env", "apps/api/.env"):
        path = Path(filename)
        if not path.exists():
            continue
        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip(";").strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_ROOT}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed: HTTP {exc.code}: {detail}") from exc


def choose_model(model_ids: list[str]) -> str:
    explicit = os.environ.get("OPENAI_SMOKE_MODEL")
    if explicit:
        if explicit not in model_ids:
            raise RuntimeError(f"OPENAI_SMOKE_MODEL={explicit!r} is not available on this key")
        return explicit

    preferred_models = (
        "gpt-4.1-mini",
        "gpt-5-mini",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-5",
        "gpt-4o",
    )
    for model_id in preferred_models:
        if model_id in model_ids:
            return model_id
    raise RuntimeError("No GPT model found in /models response")


def run_response(model: str, tools: list[dict[str, Any]] | None, prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "max_output_tokens": 120,
        "store": False,
    }
    if tools is not None:
        payload["tools"] = tools
    return request_json("POST", "/responses", payload)


def summarize_response(response: dict[str, Any]) -> dict[str, Any]:
    text_parts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                text_parts.append(content["text"])
    return {
        "id": response.get("id"),
        "status": response.get("status"),
        "output_types": [item.get("type") for item in response.get("output", [])],
        "text": (response.get("output_text") or " ".join(text_parts))[:240],
    }


def main() -> int:
    load_env()
    computer_model = os.environ.get("OPENAI_COMPUTER_USE_MODEL", "gpt-5.5")
    report: dict[str, Any] = {
        "models_listed": False,
        "minimal_response": {"ok": False},
        "web_search": {"ok": False, "tool_type": "web_search"},
        "computer_use": {"ok": False, "tool_type": "computer", "model": computer_model},
    }

    models = request_json("GET", "/models")
    model_ids = sorted(item["id"] for item in models.get("data", []) if "id" in item)
    report["models_listed"] = True
    report["available_model_count"] = len(model_ids)
    report["available_model_ids_sample"] = model_ids[:80]
    model = choose_model(model_ids)
    report["selected_text_model"] = model
    report["computer_use"]["model_available"] = computer_model in model_ids

    try:
        response = run_response(model, None, "Reply with exactly: portalpilot-ok")
        report["minimal_response"] = {"ok": True, **summarize_response(response)}
    except Exception as exc:  # noqa: BLE001 - smoke script should continue subchecks.
        report["minimal_response"] = {"ok": False, "reason": str(exc)}

    try:
        response = run_response(
            model,
            [{"type": "web_search"}],
            "Search the web for the official OpenAI homepage and answer in one short sentence.",
        )
        output_types = [item.get("type") for item in response.get("output", [])]
        report["web_search"] = {
            "ok": "web_search_call" in output_types or bool(response.get("output_text")),
            "tool_type": "web_search",
            **summarize_response(response),
        }
    except Exception as exc:  # noqa: BLE001 - smoke script should continue subchecks.
        report["web_search"] = {"ok": False, "tool_type": "web_search", "reason": str(exc)}

    try:
        payload = {
            "model": computer_model,
            "input": "Open about:blank and stop after observing the blank page.",
            "max_output_tokens": 120,
            "store": False,
            "tools": [{"type": "computer"}],
        }
        response = request_json("POST", "/responses", payload)
        output_types = [item.get("type") for item in response.get("output", [])]
        report["computer_use"] = {
            "ok": "computer_call" in output_types or response.get("status") in {"completed", "requires_action"},
            "tool_type": "computer",
            "model": computer_model,
            **summarize_response(response),
        }
    except Exception as exc:  # noqa: BLE001 - smoke script should report all failures.
        report["computer_use"] = {
            "ok": False,
            "tool_type": "computer",
            "model": computer_model,
            "model_available": computer_model in model_ids,
            "reason": str(exc),
        }

    print(json.dumps(report, indent=2))
    if not (
        report["models_listed"]
        and report["minimal_response"]["ok"]
        and report["web_search"]["ok"]
        and report["computer_use"]["ok"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
