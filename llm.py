"""
llm.py — thin wrapper around the OpenAI Chat Completions API.

This is deliberately isolated so the rest of the app never talks to OpenAI
directly. In a later phase we hand `tools` (converted from the MCP tool
catalogue) into `chat()`, and read back any tool calls the model wants to make.
Swapping OpenAI for another provider means editing only this file.
"""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

# Model is configurable via .env so attendees can downgrade for cost if needed.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Make the message list safe for OpenAI's strict tool-call rules:
      1. Every assistant `tool_calls` entry must have a matching `tool` response.
      2. Each `tool` response must come IMMEDIATELY AFTER that assistant message.
    Approval pauses and Streamlit reruns can leave responses missing or out of
    order; this rebuilds a valid sequence. It never mutates the caller's list.

    - Assistant tool_calls with no response yet are dropped (kept as plain text
      if they had any). An assistant left with neither text nor calls is removed.
    - Tool responses are re-slotted right after their assistant message; orphan
      tool messages (no matching call) are dropped.
    """
    # map tool_call_id -> its response message (last one wins)
    responses: dict[str, dict[str, Any]] = {}
    for m in messages:
        if m.get("role") == "tool" and m.get("tool_call_id"):
            responses[m["tool_call_id"]] = m

    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "tool":
            continue  # we re-insert these in the right place below
        if role == "assistant" and m.get("tool_calls"):
            kept = [tc for tc in m["tool_calls"] if tc.get("id") in responses]
            if kept:
                nm = dict(m)
                nm["tool_calls"] = kept
                out.append(nm)
                # place each response immediately after
                for tc in kept:
                    out.append(responses[tc["id"]])
            elif (m.get("content") or "").strip():
                nm = dict(m)
                nm.pop("tool_calls", None)
                out.append(nm)
            # else drop entirely
        else:
            out.append(m)
    return out


class LLMClient:
    """Minimal OpenAI client wrapper for the agent loop."""

    def __init__(self, model: str | None = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self.client = OpenAI(api_key=api_key)
        self.model = model or DEFAULT_MODEL
        self.last_usage = {"prompt": 0, "completion": 0, "total": 0}

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        """
        Send the conversation to OpenAI and return the raw message object.

        `tools` uses OpenAI's function-calling schema. In Phase 1 it's always
        None (plain chat). From Phase 2 on, mcp_manager supplies the tool list
        and this same call lets the model request tool calls.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": _sanitize_messages(messages),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        # Stash token usage so the app can read it after each call.
        u = getattr(response, "usage", None)
        if u is not None:
            self.last_usage = {
                "prompt": u.prompt_tokens,
                "completion": u.completion_tokens,
                "total": u.total_tokens,
            }
        else:
            self.last_usage = {"prompt": 0, "completion": 0, "total": 0}
        return response.choices[0].message

    @staticmethod
    def get_tool_calls(message: Any) -> list[Any]:
        """Return the tool calls on a message, or an empty list if none."""
        return list(getattr(message, "tool_calls", None) or [])