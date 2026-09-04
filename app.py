"""
app.py — Streamlit host for the AI Testing Mastery MCP workshop.

A polished chat UI that connects to MCP servers, discovers their tools, runs the
OpenAI-driven agent loop, and gates real-world actions (send/delete/create)
behind an explicit human approval step.

Run:  streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from llm import LLMClient
from mcp_manager import MCPManager

load_dotenv()

SYSTEM_PROMPT = (
    "You are a QA engineering assistant for the AI Testing Mastery program. "
    "You help with test planning, bug reporting, and quality workflows. "
    "Use the available tools when they fit the request. Be concise and practical."
)

CONFIG_PATH = Path(__file__).parent / "config" / "servers.json"
MAX_TOOL_ROUNDS = 5

# Per-server display metadata: icon + short description + accent colour.
SERVER_META = {
    "qa":    {"icon": "🧩", "label": "Custom QA server", "desc": "Your own tool, resource & prompt", "color": "#2E7D63"},
    "rag":   {"icon": "📚", "label": "RAG retrieval",     "desc": "Searches your documents",          "color": "#2E7D63"},
    "jira":  {"icon": "🗂️", "label": "Jira Cloud",         "desc": "Reads tickets (read-only)",        "color": "#B26A1B"},
    "gmail": {"icon": "✉️", "label": "Gmail",              "desc": "Reads & sends (gated)",            "color": "#B26A1B"},
}
DEFAULT_META = {"icon": "🔌", "label": "", "desc": "", "color": "#555"}

# Plain-English description of what each tool does + why the agent reaches for it.
# Used to explain sources under each answer.
TOOL_INFO = {
    "format_bug_report":     ("🧩", "qa",    "Formatted your notes into a standard bug report"),
    "qa://checklist":        ("🧩", "qa",    "Pulled the QA checklist"),
    "write_test_cases":      ("🧩", "qa",    "Used the test-case prompt template"),
    "search_docs":           ("📚", "rag",   "Searched your documents for relevant info"),
    "jira_search":           ("🗂️", "jira",  "Searched your Jira issues"),
    "jira_get_issue":        ("🗂️", "jira",  "Read a specific Jira ticket"),
    "jira_create_issue":     ("🗂️", "jira",  "Created a Jira ticket"),
    "jira_update_issue":     ("🗂️", "jira",  "Updated a Jira ticket"),
    "jira_add_comment":      ("🗂️", "jira",  "Added a comment in Jira"),
    "jira_transition_issue": ("🗂️", "jira",  "Changed a Jira ticket's status"),
    "gmail_list_messages":   ("✉️", "gmail", "Listed emails from your inbox"),
    "gmail_search_messages": ("✉️", "gmail", "Searched your Gmail"),
    "gmail_get_message":     ("✉️", "gmail", "Read a specific email"),
    "gmail_send_message":    ("✉️", "gmail", "Sent an email"),
}


def describe_tool(name: str) -> tuple[str, str, str]:
    """Return (icon, server, why) for a tool, with a sensible fallback."""
    if name in TOOL_INFO:
        return TOOL_INFO[name]
    # fallback: infer server from prefix
    server = name.split("_")[0] if "_" in name else "tool"
    return ("🔧", server, f"Ran {name}")


def extract_doc_sources(result: str) -> list[str]:
    """Pull '[source: filename]' tags out of a RAG result string."""
    import re
    return list(dict.fromkeys(re.findall(r"\[source:\s*([^\]]+)\]", result)))


def render_sources(sources: list[dict]) -> None:
    """Render the 'Sources' panel under an answer."""
    if not sources:
        with st.expander("🔎 Sources — none (answered directly, no tools used)"):
            st.markdown(
                "<span class='src-none'>The assistant answered from its own reasoning — "
                "no documents, Jira, or Gmail were consulted for this reply.</span>",
                unsafe_allow_html=True,
            )
        return

    label = f"🔎 Sources — {len(sources)} tool call{'s' if len(sources) != 1 else ''} used"
    with st.expander(label):
        for s in sources:
            docs_html = ""
            if s["docs"]:
                docs_html = "<div>" + "".join(
                    f"<span class='src-doc'>📄 {d}</span>" for d in s["docs"]
                ) + "</div>"
            st.markdown(
                f"""<div class="src-row">
                  <span class="ic">{s['icon']}</span>
                  <span class="bd"><b>{s['server']}</b> · {s['why']}
                  <span class="tl">({s['tool']})</span>{docs_html}</span>
                </div>""",
                unsafe_allow_html=True,
            )
        st.caption("Shows which tools were consulted — the assistant writes the final answer from these.")

st.set_page_config(
    page_title="AI Testing Mastery — MCP Agent",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- custom styling ---------------------------------------------------------
st.markdown(
    """
    <style>
      /* tighten the top padding */
      .block-container { padding-top: 2.2rem; padding-bottom: 5rem; }
      /* header band */
      .hero {
        border: 1px solid rgba(140,140,140,.25);
        border-radius: 16px;
        padding: 18px 22px;
        margin-bottom: 14px;
        background: linear-gradient(180deg, rgba(120,140,200,.06), rgba(120,140,200,0));
      }
      .hero h1 { font-size: 1.55rem; margin: 0 0 2px 0; font-weight: 650; }
      .hero p  { margin: 0; color: #8a8a8a; font-size: .93rem; }
      .stat-row { display:flex; gap:26px; margin-top:12px; }
      .stat b { font-size: 1.15rem; }
      .stat span { color:#8a8a8a; font-size:.8rem; display:block; margin-top:-2px; }
      /* server card in sidebar */
      .srv {
        border:1px solid rgba(140,140,140,.22);
        border-left:4px solid var(--c);
        border-radius:10px; padding:9px 11px; margin-bottom:8px;
      }
      .srv .nm { font-weight:600; font-size:.9rem; }
      .srv .ds { color:#8a8a8a; font-size:.76rem; margin-bottom:5px; }
      .srv code { font-size:.72rem; }
      /* capability chips */
      .caps { display:flex; flex-wrap:wrap; gap:7px; margin:2px 0 4px; }
      .cap {
        border:1px solid rgba(140,140,140,.25); border-radius:999px;
        padding:3px 11px; font-size:.8rem; color:#666;
      }
      /* sources panel under answers */
      .src-row { display:flex; align-items:flex-start; gap:8px; padding:5px 0; }
      .src-row .ic { font-size:1rem; line-height:1.3; }
      .src-row .bd { font-size:.83rem; }
      .src-row .tl { font-family:monospace; font-size:.76rem; color:#888; }
      .src-doc {
        display:inline-block; background:rgba(120,160,120,.14);
        border:1px solid rgba(120,160,120,.3); border-radius:6px;
        padding:1px 7px; margin:2px 4px 0 0; font-size:.75rem;
      }
      .src-none { color:#999; font-size:.83rem; font-style:italic; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_mcp() -> MCPManager:
    servers = json.loads(CONFIG_PATH.read_text())
    manager = MCPManager()
    manager.connect(servers)
    return manager


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if "tool_log" not in st.session_state:
        st.session_state.tool_log = []
    if "pending_action" not in st.session_state:
        st.session_state.pending_action = None
    if "turn_sources" not in st.session_state:
        st.session_state.turn_sources = []
    if "answer_sources" not in st.session_state:
        st.session_state.answer_sources = {}  # message index -> sources list
    if "llm" not in st.session_state:
        try:
            st.session_state.llm = LLMClient()
            st.session_state.llm_error = None
        except Exception as exc:  # noqa: BLE001
            st.session_state.llm = None
            st.session_state.llm_error = str(exc)


init_state()

mcp_error = None
try:
    mcp = get_mcp()
except Exception as exc:  # noqa: BLE001
    mcp = None
    mcp_error = str(exc)


def run_agent_turn():
    """Drive one user turn. Returns final text, or None if paused for approval.
    Accumulates the tools used this turn into st.session_state.turn_sources."""
    tools = mcp.tools if mcp else None

    for _ in range(MAX_TOOL_ROUNDS):
        message = st.session_state.llm.chat(st.session_state.messages, tools=tools)
        tool_calls = st.session_state.llm.get_tool_calls(message)

        if not tool_calls:
            return message.content or "(no response)"

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            if mcp and mcp.needs_confirmation(name):
                st.session_state.pending_action = {
                    "tool_call_id": tc.id, "name": name, "args": args,
                }
                return None

            result = mcp.call_tool(name, args)
            _record_source(name, result)
            st.session_state.tool_log.append(
                json.dumps({"tool": name, "args": args, "result": result[:400]}, indent=2)
            )
            st.session_state.messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": result}
            )

    return "Stopped after too many tool calls — please refine your request."


def _record_source(name: str, result: str) -> None:
    """Log one tool use (icon, server, why, and any RAG doc names) for this turn."""
    icon, server, why = describe_tool(name)
    st.session_state.turn_sources.append(
        {"icon": icon, "server": server, "tool": name, "why": why,
         "docs": extract_doc_sources(result)}
    )


def resume_after_confirmation(approved: bool) -> str:
    pending = st.session_state.pop("pending_action")
    if approved:
        result = mcp.call_tool(pending["name"], pending["args"])
        _record_source(pending["name"], result)
        st.session_state.tool_log.append(
            json.dumps(
                {"tool": pending["name"], "args": pending["args"], "result": result[:400]},
                indent=2,
            )
        )
    else:
        result = "User declined to run this action."
    st.session_state.messages.append(
        {"role": "tool", "tool_call_id": pending["tool_call_id"], "content": result}
    )
    answer = run_agent_turn()
    return answer if answer is not None else "(waiting for another confirmation)"


# --- sidebar ----------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔌 Connected servers")
    if mcp_error:
        st.error(f"MCP connection failed: {mcp_error}")
    elif mcp:
        for server_name, tool_names in mcp.server_tools.items():
            m = SERVER_META.get(server_name, DEFAULT_META)
            tools_html = " ".join(f"<code>{t}</code>" for t in tool_names[:6])
            more = f" +{len(tool_names) - 6} more" if len(tool_names) > 6 else ""
            st.markdown(
                f"""<div class="srv" style="--c:{m['color']}">
                <div class="nm">{m['icon']} {server_name} · {m['label']}</div>
                <div class="ds">{m['desc']}</div>
                {tools_html}{more}
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("### 🛠️ Recent tool calls")
    if st.session_state.tool_log:
        for entry in reversed(st.session_state.tool_log[-6:]):
            st.code(entry, language="json")
    else:
        st.caption("Tool calls will appear here as the agent works.")

    if st.button("🧹 Clear conversation", use_container_width=True):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.tool_log = []
        st.session_state.pending_action = None
        st.session_state.turn_sources = []
        st.rerun()


# --- header -----------------------------------------------------------------
if st.session_state.llm_error:
    st.error(f"LLM not ready: {st.session_state.llm_error}")
    st.stop()

server_count = len(mcp.server_tools) if mcp else 0
tool_count = len(mcp.tools) if mcp else 0

st.markdown(
    f"""<div class="hero">
      <h1>🧪 AI Testing Mastery — MCP Agent</h1>
      <p>One OpenAI-driven agent, many tools. Ask in plain English — it picks the right tool, calls it, and answers.</p>
      <div class="stat-row">
        <div class="stat"><b>{server_count}</b><span>MCP servers</span></div>
        <div class="stat"><b>{tool_count}</b><span>tools available</span></div>
        <div class="stat"><b>🔒</b><span>real actions gated</span></div>
      </div>
    </div>""",
    unsafe_allow_html=True,
)

# capability chips + expandable "what can this do?"
st.markdown(
    """<div class="caps">
      <span class="cap">📝 Format bug reports</span>
      <span class="cap">📚 Search your docs</span>
      <span class="cap">🗂️ Read Jira tickets</span>
      <span class="cap">✉️ Read & send email</span>
      <span class="cap">🔗 Chain tools across servers</span>
    </div>""",
    unsafe_allow_html=True,
)

with st.expander("💡 What can I ask? — example prompts"):
    st.markdown(
        "- **Bug report:** *Format this as a bug report: login button does nothing on Chrome, severity high*\n"
        "- **Docs (RAG):** *What known bugs affect the login page?*\n"
        "- **Jira:** *Search my Jira with JQL `project = TEST ORDER BY created DESC`*\n"
        "- **Gmail:** *Search my Gmail for my most recent emails*\n"
        "- **Multi-server chain:** *Find the Chrome login bug in our docs, format it as a bug report, then email it to me*\n"
        "\n_Sending email pauses for your approval before it goes out._"
    )

st.divider()

# --- transcript -------------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] in ("system", "tool"):
        continue
    if msg["role"] == "assistant" and not msg.get("content"):
        continue
    avatar = "🧑‍💻" if msg["role"] == "user" else "🧪"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            render_sources(msg["sources"])


# --- pending-action confirmation gate ---------------------------------------
if st.session_state.pending_action:
    pa = st.session_state.pending_action
    st.warning("⚠️ **Approval needed** — the agent wants to run a real action.")
    with st.chat_message("assistant", avatar="🔒"):
        st.markdown(f"Run **`{pa['name']}`** with these arguments?")
        st.code(json.dumps(pa["args"], indent=2), language="json")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Approve & run", use_container_width=True, type="primary"):
                with st.spinner("Running..."):
                    answer = resume_after_confirmation(approved=True)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer,
                     "sources": list(st.session_state.turn_sources)}
                )
                st.rerun()
        with c2:
            if st.button("❌ Cancel", use_container_width=True):
                answer = resume_after_confirmation(approved=False)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer,
                     "sources": list(st.session_state.turn_sources)}
                )
                st.rerun()
    st.stop()


# --- chat input -------------------------------------------------------------
if prompt := st.chat_input("Ask about test plans, bugs, Jira, email..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.turn_sources = []  # fresh source list for this turn
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧪"):
        with st.spinner("Thinking..."):
            answer = run_agent_turn()
        if answer is None:
            st.rerun()
        st.markdown(answer)
        render_sources(st.session_state.turn_sources)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": list(st.session_state.turn_sources)}
    )
    st.rerun()