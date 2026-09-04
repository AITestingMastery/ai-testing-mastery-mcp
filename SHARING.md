# Sharing this repo safely

This project holds **real secrets** on your machine — your OpenAI key, Jira
token, Gmail OAuth client, and a cached Gmail token. None of them should ever
reach GitHub. Follow this before pushing.

## Step 1 — Safety check (run these first)

From the project folder:

```bash
# A. Confirm the secret files are IGNORED (each line should print the filename)
git check-ignore .env gmail_credentials.json credentials.json token.json
```

If a filename prints, it's safely ignored. If a filename does **not** print,
stop — it is not ignored and would be committed. Fix `.gitignore` before going on.

```bash
# B. See exactly what WOULD be committed — read this list carefully
git add -A
git status
```

Look at the "Changes to be committed" list. It should contain code, README,
CAPABILITIES.md, config, and sample_docs — and **none** of:
`.env`, `gmail_credentials.json`, `credentials.json`, `token.json`, `chroma_db/`.

```bash
# C. Belt-and-braces: grep staged content for anything secret-looking
git diff --cached | grep -iE "sk-|api_token|OPENAI_API_KEY=|client_secret|refresh_token" || echo "clean"
```

If it prints `clean`, nothing secret is staged. If it prints matches, unstage
that file (`git restore --staged <file>`) and add it to `.gitignore`.

## Step 2 — First push to GitHub

```bash
# initialise (skip if the repo already exists)
git init
git add -A
git commit -m "AI Testing Mastery MCP agent — workshop repo"

# create an EMPTY repo on github.com first (no README), then:
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

## Step 3 — Tell people what to add

Attendees clone the repo and supply their **own** secrets — you share code, never
keys. Point them at `README.md` → Quick start. They will each:
1. `cp .env.example .env` and fill in their own values
2. run the Gmail `auth` step to make their own `token.json`
3. use their own Jira and OpenAI keys

## If you ever commit a secret by accident

A secret pushed to GitHub is compromised even after deletion — the fix is to
**rotate it**, not just remove it:
- OpenAI key → revoke at platform.openai.com, make a new one
- Jira token → revoke at id.atlassian.com, make a new one
- Gmail → delete the OAuth client in Google Cloud Console, create a new one

Then remove the file from history (e.g. `git rm --cached <file>`, commit) and
force-push, or use `git filter-repo` for a full history scrub.

## The golden rule

Share **code and config**, never **credentials**. The repo is designed for this:
every secret is a file path or env var in `.env`, and `.gitignore` blocks them all.
