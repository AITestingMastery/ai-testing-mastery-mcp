# AI Testing Mastery — MCP Agent: Capabilities & Architecture

A one-page reference for what this app is, what it can do, and how it's wired.

## What it is

A single AI **agent** with a web UI (Streamlit). You type a request in plain
English; **OpenAI** decides which tool to use; the app calls that tool over the
**Model Context Protocol (MCP)**; the result comes back and the agent answers.
No Claude Desktop needed — it runs as one shareable Python app.

## Architecture (the flow)

```
You (browser)
      │  type a request
      ▼
Streamlit host + agent loop        ← chat UI, sidebar, tool log, approval gate
      │
      ├──────────────┐
      ▼              ▼
OpenAI (brain)   MCP manager        ← discovers tools, routes each call
                     │
      ┌──────────────┴───────────────┐
      ▼ Local (stdio)                ▼ Remote (HTTP + auth)
  ┌─────────┐  ┌─────────┐      ┌─────────┐  ┌─────────┐
  │  qa     │  │  rag    │      │  jira   │  │  gmail  │
  │ your    │  │ doc     │      │ tickets │  │ email   │
  │ server  │  │ search  │      │ (read)  │  │ (gated) │
  └─────────┘  └─────────┘      └─────────┘  └─────────┘
```

The loop: send the user message + available tools to OpenAI → if OpenAI asks
for a tool, the manager runs it and feeds the result back → repeat until OpenAI
gives a final answer. Real actions pause at the approval gate first.

## Capabilities by server

### qa — your custom MCP server
- **format_bug_report** — turn rough notes into a standardized bug report
- **qa://checklist** (resource) — a reusable pre-release QA checklist
- **write_test_cases** (prompt) — a reusable test-case-writing template

### rag — retrieval over your documents
- **search_docs** — semantic search across your files (test plans, known bugs,
  API cases); grounds answers in your own content, not just the model's memory
- Swap the files in `sample_docs/` to make it domain-aware for any team

### jira — real Jira Cloud (read-only)
- **jira_search** — find issues with JQL (e.g. `project = TEST ORDER BY created DESC`)
- **jira_get_issue** — read a specific ticket's details
- Read-only is enforced at the server, so the agent can't change your Jira

### gmail — real Gmail (read + send)
- Search and read your inbox, read threads, list labels
- **Send email**, create drafts, reply — sending is gated by your approval

## Cross-server workflows (the headline feature)

The agent can chain tools from different servers in one request. Example:

> *"Find the Chrome login bug in our docs, format it as a bug report, then
> email it to me."*

runs **rag** (find the bug) → **qa** (format it) → **gmail** (send it, after
you approve) — one sentence, three servers.

## Safety: human-in-the-loop

Any tool whose action is real and hard to undo — anything matching
*send, delete, trash, create, update, reply* — does **not** run automatically.
The app pauses, shows you the exact tool and arguments, and waits for
**Approve** or **Cancel**. This is enforced in the host, not left to the model.

## How to make it your own

1. Drop your own files into `sample_docs/` (RAG indexes them).
2. Edit `servers/qa_server.py` — rename the tool, change the logic.
3. Point `jira`/`gmail` at your own accounts via `.env`.
4. Add any other MCP server in `config/servers.json`.
