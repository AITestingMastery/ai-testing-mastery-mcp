"""
servers/rag_server.py — RAG exposed as an MCP tool (Phase 3).

This is the Session 1 "MCP + RAG are complementary" idea in code: RAG arrives as
just another MCP tool the agent can call. The host doesn't know or care that
`search_docs` is backed by embeddings — it's discovered and called like any tool.

How it works:
  1. On startup, read every file in sample_docs/, split into chunks.
  2. Embed each chunk with OpenAI embeddings.
  3. Store vectors in a local Chroma collection (persisted to chroma_db/).
  4. Expose one tool, search_docs(query), that embeds the query and returns
     the most similar chunks.

Rebuild note: the index is built once and persisted. Delete the chroma_db/
folder (git-ignored) to force a rebuild after changing sample_docs/.

Requires OPENAI_API_KEY in the environment (loaded from .env by the host, or
set directly when running this server standalone).
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from openai import OpenAI

load_dotenv()

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
DOCS_DIR = Path(__file__).parent.parent / "sample_docs"
DB_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION = "qa_docs"
CHUNK_CHARS = 600  # rough chunk size; small docs so char-based is fine

mcp = MCPServer("rag-server")
_openai = OpenAI()  # reads OPENAI_API_KEY from env


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts with OpenAI; returns one vector per text."""
    resp = _openai.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def _chunk(text: str) -> list[str]:
    """Split a document into ~CHUNK_CHARS pieces on paragraph boundaries."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paras:
        if len(current) + len(para) + 2 <= CHUNK_CHARS:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def _build_index() -> chromadb.Collection:
    """Load docs, embed, and store in Chroma. Reuses the index if already built."""
    client = chromadb.PersistentClient(path=str(DB_DIR))

    existing = [c.name for c in client.list_collections()]
    if COLLECTION in existing:
        col = client.get_collection(COLLECTION)
        if col.count() > 0:
            return col  # already built
        client.delete_collection(COLLECTION)

    col = client.create_collection(COLLECTION)

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        for i, chunk in enumerate(_chunk(path.read_text(encoding="utf-8"))):
            ids.append(f"{path.stem}-{i}")
            docs.append(chunk)
            metas.append({"source": path.name})

    if docs:
        embeddings = _embed(docs)
        col.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=metas)
    return col


# Build once at import so the first tool call is fast.
_collection = _build_index()


@mcp.tool()
def search_docs(query: str, top_k: int = 3) -> str:
    """
    Search the QA knowledge base (test plans, known bugs, API cases) and return
    the most relevant passages.

    Args:
        query: What to look for, in natural language.
        top_k: How many passages to return (default 3).
    """
    query_vec = _embed([query])[0]
    results = _collection.query(query_embeddings=[query_vec], n_results=top_k)

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    if not docs:
        return "No relevant passages found."

    blocks = []
    for doc, meta in zip(docs, metas):
        source = meta.get("source", "unknown") if meta else "unknown"
        blocks.append(f"[source: {source}]\n{doc}")
    return "\n\n---\n\n".join(blocks)


if __name__ == "__main__":
    mcp.run(transport="stdio")
