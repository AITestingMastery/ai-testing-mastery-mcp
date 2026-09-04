"""
mcp_manager.py — the MCP client side of the host.

Responsibilities:
  • launch each configured MCP server (stdio) and run the Initialize→Discover
    handshake — this is the Session 2 lifecycle, in code
  • hold the combined tool catalogue across all servers
  • convert MCP tool schemas → OpenAI function-calling schema
  • route a tool call from the model to the server that owns it

Design note: MCP's Python client is async and each connection is a context
manager. Streamlit is synchronous, so we keep one persistent asyncio event
loop in a background thread and hand it coroutines via run_coroutine_threadsafe.
This keeps servers alive across Streamlit reruns (v2 Client stays open).
"""

from __future__ import annotations

import asyncio
import os
import threading
from contextlib import AsyncExitStack
from typing import Any

from mcp import Client, StdioServerParameters


class MCPManager:
    """Manages MCP server connections and exposes a sync API for Streamlit."""

    def __init__(self) -> None:
        # persistent event loop in a background thread
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self._stack: AsyncExitStack | None = None
        self._clients: dict[str, Client] = {}          # server_name -> Client
        self._tool_owner: dict[str, str] = {}          # tool_name  -> server_name
        self.tools: list[dict[str, Any]] = []          # OpenAI-format tool schemas
        self.server_tools: dict[str, list[str]] = {}   # server_name -> [tool names]

    # --- background loop plumbing -------------------------------------------
    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run(self, coro: Any) -> Any:
        """Run a coroutine on the background loop and block for its result."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    # --- public sync API -----------------------------------------------------
    def connect(self, servers: dict[str, dict[str, Any]]) -> None:
        """
        Connect to every server in the config and discover their tools.

        `servers` maps a name to {"command": str, "args": [str], "env": {...}}.
        """
        self._run(self._connect_all(servers))

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool by name on whichever server owns it; return text."""
        return self._run(self._call_tool(tool_name, arguments))

    # Tools whose names contain any of these need explicit user confirmation
    # before they run — they take real, hard-to-undo actions (sending mail,
    # deleting, creating tickets). This is the Session 2 "human-in-the-loop"
    # safeguard, enforced in the host rather than trusted to the model.
    GATED_KEYWORDS = (
        "send", "delete", "trash", "create", "update", "reply",
        "comment", "transition", "add", "modify", "move", "assign",
    )

    def needs_confirmation(self, tool_name: str) -> bool:
        """True if a tool should pause for human approval before running."""
        lowered = tool_name.lower()
        return any(kw in lowered for kw in self.GATED_KEYWORDS)

    # --- async internals -----------------------------------------------------
    async def _connect_all(self, servers: dict[str, dict[str, Any]]) -> None:
        self._stack = AsyncExitStack()

        for name, cfg in servers.items():
            params = StdioServerParameters(
                command=cfg["command"],
                args=cfg.get("args", []),
                env=self._resolve_env(cfg.get("env")),
            )
            # keep each client open for the app's lifetime
            client = await self._stack.enter_async_context(Client(params))
            self._clients[name] = client

            listed = await client.list_tools()
            names: list[str] = []
            for tool in listed.tools:
                # Tool names must be unique across servers — OpenAI routes by name
                # alone. If two servers expose the same tool name, the later one
                # wins and we warn, so attendees notice the collision.
                if tool.name in self._tool_owner:
                    print(
                        f"[MCPManager] WARNING: tool '{tool.name}' exists on both "
                        f"'{self._tool_owner[tool.name]}' and '{name}'; using '{name}'."
                    )
                self._tool_owner[tool.name] = name
                names.append(tool.name)
                self.tools.append(self._to_openai_schema(tool))
            self.server_tools[name] = names

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        owner = self._tool_owner.get(tool_name)
        if owner is None:
            return f"Error: no server owns tool '{tool_name}'."
        client = self._clients[owner]
        result = await client.call_tool(tool_name, arguments)
        # v2 returns content blocks; join any text parts
        parts = [c.text for c in (result.content or []) if hasattr(c, "text")]
        return "\n".join(parts) if parts else "(tool returned no text)"

    @staticmethod
    def _resolve_env(env: dict[str, str] | None) -> dict[str, str] | None:
        """
        Expand ${VAR} placeholders in a server's env block using the host's real
        environment, and merge over the inherited environment so the child
        process still sees PATH etc.

        This keeps secrets in .env (loaded into os.environ by the host) rather
        than hard-coded in config/servers.json — so the repo is safe to share.
        A placeholder whose variable is unset resolves to "", which servers like
        mcp-atlassian treat as "not configured".
        """
        if not env:
            return None
        resolved = dict(os.environ)  # inherit base env (PATH, etc.)
        for key, value in env.items():
            resolved[key] = os.path.expandvars(value) if isinstance(value, str) else value
        return resolved

    @staticmethod
    def _to_openai_schema(tool: Any) -> dict[str, Any]:
        """Convert one MCP tool into OpenAI's function-calling format."""
        # v2 wire types are snake_case: tool.input_schema
        schema = getattr(tool, "input_schema", None) or {
            "type": "object", "properties": {}
        }
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            },
        }