# AI Testing Mastery — MCP Agent

A hands-on Model Context Protocol (MCP) workshop app. A **Streamlit** UI acts as
an MCP **host**: it talks to **OpenAI**, connects to four MCP **servers** — a
custom QA server, a RAG document-search server, Jira, and Gmail — and runs the
agent loop in a UI you can watch. Real-world actions (send email, create a Jira
ticket) pause for your approval first.

No Claude Desktop required. Clone, add your keys, run.

See **CAPABILITIES.md** for the full architecture and what each server can do.

---

## Quick start (5 steps)

```bash
# 1. install dependencies
pip install -r requirements.txt

# 2. copy the env template and fill in your values
cp .env.example .env        # Windows: copy .env.example .env

# 3. (one time) authorize Gmail — opens a browser, sign in, approve
#    Windows (cmd):  copy gmail_credentials.json credentials.json
uvx --with "mcp<2" --from mcp-google-gmail mcp-google-gmail auth

# 4. (optional) pre-warm the Jira server so first launch is fast
uvx mcp-atlassian --help

# 5. run
streamlit run app.py
```

Open the browser tab it prints. If a server fails, the sidebar shows the error.

---

## What you need to fill into `.env`

| Variable | What it is | Where to get it |
|---|---|---|
| `OPENAI_API_KEY` | Drives the agent loop + RAG embeddings | platform.openai.com |
| `JIRA_URL` | `https://YOURNAME.atlassian.net` (no trailing slash) | your Jira site |
| `JIRA_USERNAME` | The **email** on your Atlassian account | — |
| `JIRA_API_TOKEN` | Classic API token | id.atlassian.com → API tokens |
| `GMAIL_CREDENTIALS_PATH` | Path to your OAuth client JSON | Google Cloud Console (Desktop app) |

Gmail also needs a one-time Google Cloud setup: create a project, enable the
Gmail API, configure the OAuth consent screen (add yourself as a **test user**),
create a **Desktop app** OAuth client, and download the JSON.

---

## Servers (this repo)

| Server | Type | Does | Safety |
|---|---|---|---|
| `qa` | local (stdio) | Format bug reports; QA checklist; test-case prompt | — |
| `rag` | local (stdio) | Semantic search over `sample_docs/` | — |
| `jira` | remote | Search/read **and** create/update issues | writes gated |
| `gmail` | remote | Read **and** send email | sends gated |

**Human-in-the-loop:** any tool whose name implies a real action (send, delete,
create, update, comment, transition, …) pauses for an Approve/Cancel click
before it runs. Enforced in the host — see `MCPManager.needs_confirmation`.

---

## Try it

- **Bug report:** *Format this as a bug report: login button does nothing on Chrome, severity high*
- **Docs (RAG):** *What known bugs affect the login page?*
- **Jira read:** *Search my Jira with JQL `project = TEST ORDER BY created DESC`*
- **Jira write (gated):** *Create a Jira ticket in TEST titled "Login button bug"* → Approve
- **Gmail (gated):** *Email a summary of open bugs to me@example.com* → Approve
- **Multi-server chain:** *Find the Chrome login bug in our docs, format it as a bug report, then email it to me*

---

## SDK version note

Uses the MCP Python SDK **v2** (`mcp>=2,<3`) — `FastMCP` is now `MCPServer`.
The Gmail server was written for v1, so it's launched with `mcp<2` pinned
(`uvx --with "mcp<2" ...`). Both are handled for you in `config/servers.json`.

---

## Make it your own

1. Drop your own files into `sample_docs/` — delete `chroma_db/` to re-index.
2. Edit `servers/qa_server.py` — rename the tool, change the logic.
3. Point `jira` / `gmail` at your own accounts via `.env`.
4. Add any other MCP server in `config/servers.json`.

---

## Files never to commit

`.env`, `gmail_credentials.json`, `credentials.json`, `token.json`, `chroma_db/`
— all already in `.gitignore`. See **SHARING.md** before pushing to GitHub.