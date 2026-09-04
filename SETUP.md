# Setup guide

Everything you need to get this app running against **your own** accounts. About
15–20 minutes end to end. Each person who clones the repo does this once — no
credentials are ever shared through the repo.

**Contents**
1. Prerequisites
2. Get the code & install
3. OpenAI key (required)
4. Jira (optional)
5. Gmail (optional)
6. Run it
7. Troubleshooting

---

## 1. Prerequisites

Install these first, then check each in a terminal:

| Tool | Check | Get it |
|---|---|---|
| Python 3.10+ | `python --version` | python.org (tick "Add to PATH") |
| Node.js 18+ | `node --version` | nodejs.org (LTS) |
| uv | `uv --version` | `powershell -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Git | `git --version` | git-scm.com |

You also need an **OpenAI API key**. Jira and Gmail are optional — the `qa` and
`rag` servers work without them.

---

## 2. Get the code & install

```bash
git clone https://github.com/AITestingMastery/ai-testing-mastery-mcp.git
cd ai-testing-mastery-mcp

pip install -r requirements.txt

cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` in an editor — you'll fill it in as you go through the sections below.

---

## 3. OpenAI key (required)

Drives the agent loop and the RAG embeddings.

1. Get a key at `platform.openai.com` → API keys.
2. In `.env`:
   ```
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_MODEL=gpt-4o-mini
   ```

With just this, the `qa` and `rag` servers already work. Jira and Gmail are added
below.

---

## 4. Jira (optional)

Connects to your Jira Cloud site. ~5 minutes.

### 4a. Your site URL and email
- **Site URL:** `https://YOURNAME.atlassian.net` (no trailing slash). No site?
  Create a free one at `atlassian.com/software/jira`.
- **Email:** the address you log into Atlassian with.

### 4b. Create an API token
1. Go to `id.atlassian.com/manage-profile/security/api-tokens`.
2. **Create API token** → label it `mcp-jira` → **Create**.
3. **Copy it now** — shown only once.

### 4c. Fill `.env`
```
JIRA_URL=https://YOURNAME.atlassian.net
JIRA_USERNAME=your-atlassian-email@example.com
JIRA_API_TOKEN=paste-your-token-here
```

### 4d. (Optional) pre-warm so first launch is fast
```bash
uvx mcp-atlassian --help
```

**What it can do:** `jira_search`, `jira_get_issue`, `jira_create_issue`,
`jira_update_issue`, `jira_add_comment`, `jira_transition_issue`. Write tools
pause for your approval before running; reads run freely. To make it read-only,
add `"READ_ONLY_MODE": "true"` to the `jira` env block in `config/servers.json`
and drop the write tools from `ENABLED_TOOLS`.

---

## 5. Gmail (optional)

Connects to your inbox. ~10 minutes, because Google requires OAuth. You'll end
up with two files, both git-ignored: `gmail_credentials.json` (your OAuth client)
and `token.json` (your signed-in session).

### 5a. Create a Google Cloud project & enable the Gmail API
1. Go to `console.cloud.google.com`.
2. Project dropdown → **New Project** → name `mcp-gmail` → **Create** → select it.
3. Left menu (☰) → **APIs & Services → Library**.
4. Search **Gmail API** → click it → **Enable**.

### 5b. Configure the OAuth consent screen
1. **APIs & Services → OAuth consent screen** (may appear as **Google Auth
   Platform → Branding**). Click **Get Started** / **Configure**.
2. **App name:** `mcp-gmail`; **support email:** yours. **Next**.
3. **Audience: External**. **Next**.
4. **Contact:** your email. Agree. **Continue** / **Create**.
5. **Audience** section → **Test users** → **+ Add users** → add **your own
   Gmail** → **Save**.

> Adding yourself as a test user lets you use the app without Google's full
> verification. The app stays in "Testing" mode — that's fine.

### 5c. Create OAuth credentials (Desktop app)
1. **APIs & Services → Credentials → + Create Credentials → OAuth client ID**.
2. **Application type: Desktop app** (not "Web application"). Name `mcp-desktop`
   → **Create**.
3. **Download JSON**.
4. Move it into your project folder and rename it exactly **`gmail_credentials.json`**.

### 5d. Authorize (one-time)
```bash
# Windows (cmd): the tool defaults to credentials.json, so copy it:
copy gmail_credentials.json credentials.json

# run the auth flow (all platforms):
uvx --with "mcp<2" --from mcp-google-gmail mcp-google-gmail auth
```
A browser opens:
1. Sign in with your **test-user Gmail**.
2. **"Google hasn't verified this app"** is expected → **Advanced → Go to
   mcp-gmail (unsafe)** ("unsafe" just means unverified — it's your own app).
3. Approve. The terminal saves `token.json`.

### 5e. Fill `.env`
```
GMAIL_CREDENTIALS_PATH=./gmail_credentials.json
```

---

## 6. Run it

```bash
streamlit run app.py
```

A browser tab opens. The sidebar shows each connected server and its tools. Try:

- **Bug report:** *Format this as a bug report: login button does nothing on Chrome, severity high*
- **Docs (RAG):** *What known bugs affect the login page?*
- **Jira read:** *Search my Jira with JQL `project = TEST ORDER BY created DESC`*
- **Jira write (gated):** *Create a Jira ticket in TEST titled "Login button bug"* → Approve
- **Gmail (gated):** *Email a summary of open bugs to me@example.com* → Approve
- **Multi-server chain:** *Find the Chrome login bug in our docs, format it as a bug report, then email it to me*

---

## 7. Troubleshooting

**Whole sidebar shows `TaskGroup (1 sub-exception)`** — one server failed to
start and took the group down. Run that server alone to see the real error, or
recheck its `.env` values. For Gmail, this usually means the `auth` step (5d)
wasn't completed yet.

**Gmail: `Credentials path: credentials.json` then "not found"** — the tool
didn't get your path. Easiest fix: `copy gmail_credentials.json credentials.json`
(step 5d).

**Gmail: "Access blocked / app not verified"** — you didn't add yourself as a
Test user (5b step 5), or signed in with a different Google account.

**Jira: empty results** — the issues are in a different project. Use
`jira_search` with your real project key: `project = YOURKEY ORDER BY created DESC`.
Find the key in any ticket ID (`TEST-42` → key is `TEST`).

**Jira: 401 / auth error** — the email must match the account that made the
token, and `JIRA_URL` must start with `https://` and have no trailing slash.

**A send/create just happens with no prompt** — do a full restart (Ctrl+C, then
`streamlit run app.py`). The approval gate lives in cached modules that only
reload on restart.

---

## Make it your own

1. Drop your own files into `sample_docs/` — delete `chroma_db/` to re-index.
2. Edit `servers/qa_server.py` — rename the tool, change the logic.
3. Point `jira` / `gmail` at your own accounts via `.env`.
4. Add any other MCP server in `config/servers.json`.

Before sharing your own fork, see **SHARING.md** — never commit `.env`,
`gmail_credentials.json`, `credentials.json`, or `token.json`.
