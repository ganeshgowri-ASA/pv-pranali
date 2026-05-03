"""Antaryami RAG MCP server — wraps antaryami-os RAG over Supabase pgvector.

Tools exposed:
  ingest_document  – split text into chunks, embed, upsert to Supabase
  search_chunks    – embed query, return top-k results with similarity scores
  delete_document  – remove all chunks for a doc_id
  list_documents   – list all ingested documents with chunk counts

Requires env vars: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY
Run: python -m mcp_servers.antaryami.server  (or: python server.py)
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from supabase import Client, create_client

TABLE = "doc_chunks"
EMBED_MODEL = "text-embedding-3-small"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

mcp = FastMCP("antaryami-rag")


def _supabase() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def _embed(texts: list[str]) -> list[list[float]]:
    resp = OpenAI().embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


def _chunk(text: str) -> list[str]:
    """Sliding-window character chunker."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunks.append(text[start : start + CHUNK_SIZE])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


@mcp.tool()
def ingest_document(
    doc_id: str,
    title: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Split text, embed chunks, and upsert to Supabase pgvector.

    Args:
        doc_id:   Unique identifier for the document (used as idempotency key).
        title:    Human-readable title stored alongside every chunk.
        content:  Full plain-text body of the document.
        metadata: Optional JSON metadata attached to every chunk.

    Returns:
        {"doc_id": str, "chunks_ingested": int}
    """
    db = _supabase()
    chunks = _chunk(content)
    embeddings = _embed(chunks)
    meta = metadata or {}

    rows = [
        {
            "id": str(uuid.uuid4()),
            "doc_id": doc_id,
            "title": title,
            "chunk_index": i,
            "content": chunk,
            "embedding": emb,
            "metadata": meta,
        }
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]

    # replace existing chunks so re-ingest is idempotent
    db.table(TABLE).delete().eq("doc_id", doc_id).execute()
    db.table(TABLE).insert(rows).execute()

    return {"doc_id": doc_id, "chunks_ingested": len(rows)}


@mcp.tool()
def search_chunks(
    query: str,
    top_k: int = 5,
    doc_id: str | None = None,
) -> list[dict[str, Any]]:
    """Embed query and return top-k similar chunks with similarity scores.

    Args:
        query:  Natural-language search string.
        top_k:  Maximum number of results to return (default 5).
        doc_id: Optional; restrict search to a single document.

    Returns:
        List of {doc_id, title, chunk_index, content, similarity}.
    """
    db = _supabase()
    (q_emb,) = _embed([query])

    params: dict[str, Any] = {"query_embedding": q_emb, "match_count": top_k}
    fn = "match_doc_chunks"
    if doc_id:
        params["filter_doc_id"] = doc_id
        fn = "match_doc_chunks_filtered"

    result = db.rpc(fn, params).execute()

    return [
        {
            "doc_id": row["doc_id"],
            "title": row.get("title", ""),
            "chunk_index": row.get("chunk_index", 0),
            "content": row["content"],
            "similarity": row["similarity"],
        }
        for row in (result.data or [])
    ]


@mcp.tool()
def delete_document(doc_id: str) -> dict[str, Any]:
    """Delete all stored chunks for a document.

    Args:
        doc_id: Identifier of the document to remove.

    Returns:
        {"doc_id": str, "chunks_deleted": int}
    """
    db = _supabase()
    result = db.table(TABLE).delete().eq("doc_id", doc_id).execute()
    deleted = len(result.data) if result.data else 0
    return {"doc_id": doc_id, "chunks_deleted": deleted}


@mcp.tool()
def list_documents() -> list[dict[str, Any]]:
    """List all ingested documents with their chunk counts.

    Returns:
        List of {doc_id, title, chunk_count}.
    """
    db = _supabase()
    result = db.table(TABLE).select("doc_id, title").execute()

    seen: dict[str, dict[str, Any]] = {}
    for row in result.data or []:
        did = row["doc_id"]
        if did not in seen:
            seen[did] = {"doc_id": did, "title": row.get("title", ""), "chunk_count": 0}
        seen[did]["chunk_count"] += 1

    return list(seen.values())


if __name__ == "__main__":
    mcp.run()
