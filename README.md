# AI Testing Mastery — MCP Agent

A hands-on Model Context Protocol (MCP) workshop app. A **Streamlit** UI acts as
an MCP **host**: it talks to **OpenAI**, connects to four MCP **servers** — a
custom QA server, a RAG document-search server, Jira, and Gmail — and runs the
agent loop in a UI you can watch. Real-world actions (send email, create a Jira
ticket) pause for your approval first.

No Claude Desktop required. Clone, add your keys, run.

## Docs

- **SETUP.md** — full setup, start to finish (prerequisites, OpenAI, Jira, Gmail, run)
- **CAPABILITIES.md** — architecture and what each server can do
- **SHARING.md** — how to fork/push safely without leaking secrets

## Quick start

```bash
git clone https://github.com/AITestingMastery/ai-testing-mastery-mcp.git
cd ai-testing-mastery-mcp
pip install -r requirements.txt
cp .env.example .env        # then add your OPENAI_API_KEY

streamlit run app.py
```

With just an OpenAI key, the `qa` and `rag` servers work immediately. To add
Jira and Gmail, follow **SETUP.md** (sections 4 and 5). Each person who clones
the repo sets up their **own** accounts — credentials are never shared through
the repo.

## Servers

| Server | Type | Does | Safety |
|---|---|---|---|
| `qa` | local (stdio) | Format bug reports; QA checklist; test-case prompt | — |
| `rag` | local (stdio) | Semantic search over `sample_docs/` | — |
| `jira` | remote | Search/read **and** create/update issues | writes gated |
| `gmail` | remote | Read **and** send email | sends gated |

**Human-in-the-loop:** any tool whose name implies a real action (send, delete,
create, update, comment, transition, …) pauses for an Approve/Cancel click
before it runs. Enforced in the host — see `MCPManager.needs_confirmation`.

## Try it

- **Bug report:** *Format this as a bug report: login button does nothing on Chrome, severity high*
- **Docs (RAG):** *What known bugs affect the login page?*
- **Jira read:** *Search my Jira with JQL `project = TEST ORDER BY created DESC`*
- **Jira write (gated):** *Create a Jira ticket in TEST titled "Login button bug"* → Approve
- **Gmail (gated):** *Email a summary of open bugs to me@example.com* → Approve
- **Multi-server chain:** *Find the Chrome login bug in our docs, format it as a bug report, then email it to me*

## SDK version note

Uses the MCP Python SDK **v2** (`mcp>=2,<3`) — `FastMCP` is now `MCPServer`. The
Gmail server was written for v1, so it's launched with `mcp<2` pinned
(`uvx --with "mcp<2" ...`). Both are handled in `config/servers.json`.

## Files never to commit

`.env`, `gmail_credentials.json`, `credentials.json`, `token.json`, `chroma_db/`
— all already in `.gitignore`. See **SHARING.md** before pushing.
