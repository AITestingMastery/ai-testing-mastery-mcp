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
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message

    @staticmethod
    def get_tool_calls(message: Any) -> list[Any]:
        """Return the tool calls on a message, or an empty list if none."""
        return list(getattr(message, "tool_calls", None) or [])
