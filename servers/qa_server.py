"""
servers/qa_server.py — YOUR custom MCP server (the teaching centerpiece).

Built on the official MCP Python SDK v2 (mcp>=2). It exposes one of each MCP
primitive so it's a complete, self-contained example:

  • Tool     — format_bug_report(...)  : the model can CALL this to do work
  • Resource — qa://checklist           : the model can READ this for context
  • Prompt   — write_test_cases(...)     : a reusable prompt template

Run it directly for a quick check:
    python servers/qa_server.py         # starts on stdio, waits for a client

Note (v2 API): in mcp 2.x, FastMCP was renamed to MCPServer and moved to
mcp.server.mcpserver. The @tool/@resource/@prompt decorators are unchanged.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("qa-server")


# --- TOOL: something the model can invoke to perform an action --------------
@mcp.tool()
def format_bug_report(
    title: str,
    steps: str,
    severity: str = "Medium",
    environment: str = "Not specified",
) -> str:
    """
    Turn rough notes into a clean, standardized bug report.

    Args:
        title: One-line summary of the bug.
        steps: How to reproduce it (free text; newlines become numbered steps).
        severity: One of Low, Medium, High, Critical.
        environment: Where it happened (browser/OS/build).
    """
    severity = severity.capitalize()
    valid = {"Low", "Medium", "High", "Critical"}
    if severity not in valid:
        severity = "Medium"

    # split free-text steps into a numbered list.
    # strip any numbering the caller already added (e.g. "1. ", "2) ") so we
    # don't double-number — tools should be defensive about their inputs.
    import re
    lines = []
    for s in steps.splitlines():
        s = s.strip()
        if not s:
            continue
        s = re.sub(r"^\s*\d+[.)]\s*", "", s)  # remove leading "1." or "1)"
        lines.append(s)
    numbered = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1)) or "1. (none given)"

    return (
        f"**Bug Report**\n\n"
        f"**Title:** {title}\n"
        f"**Severity:** {severity}\n"
        f"**Environment:** {environment}\n\n"
        f"**Steps to Reproduce:**\n{numbered}\n\n"
        f"**Status:** Open"
    )


# --- RESOURCE: read-only context the model can pull in ----------------------
@mcp.resource("qa://checklist")
def qa_checklist() -> str:
    """A reusable pre-release QA checklist."""
    return (
        "Pre-Release QA Checklist\n"
        "- Smoke test all critical user paths\n"
        "- Verify login, logout, and session timeout\n"
        "- Check form validation and error messages\n"
        "- Test on supported browsers and mobile viewports\n"
        "- Confirm API error handling (4xx/5xx)\n"
        "- Review accessibility basics (labels, contrast, keyboard nav)\n"
        "- Validate data persistence after refresh\n"
    )


# --- PROMPT: a reusable prompt template the host can offer ------------------
@mcp.prompt()
def write_test_cases(feature: str) -> str:
    """Generate a prompt that asks for thorough test cases for a feature."""
    return (
        f"Write a thorough set of test cases for the following feature: {feature}.\n"
        f"Include positive cases, negative cases, boundary conditions, and one "
        f"security consideration. Present them as a numbered list."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")