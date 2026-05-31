
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

_PERSIST_DIR  = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
_COLLECTION   = os.getenv("CHROMA_COLLECTION",  "yt_chunks")
_EMBED_MODEL  = os.getenv("EMBED_MODEL",         "nvidia/nv-embedqa-e5-v5")
_NVIDIA_KEY   = os.getenv("NVIDIA_API_KEY",      "")

_client: Optional[chromadb.ClientAPI] = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=_PERSIST_DIR)
        embed_fn = OpenAIEmbeddingFunction(
    api_key=_NVIDIA_KEY,
    model_name="nvidia/nv-embed-v1",
    api_base="https://integrate.api.nvidia.com/v1",
)
        _collection = _client.get_or_create_collection(
            name=_COLLECTION,
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert_chunks(
    chunks: List[Dict[str, Any]],
    video_meta: Dict[str, Any],
) -> int:
    col = _get_collection()

    ids       = [c["chunk_id"]   for c in chunks]
    documents = [c["text"]        for c in chunks]
    metadatas = [
        {
            "video_id":         c["video_id"],
            "chunk_index":      c["chunk_index"],
            "start_time":       c["start_time"],
            "end_time":         c["end_time"],
            "token_count":      c["token_count"],
            "title":            str(video_meta.get("title", "")),
            "channel_name":     str(video_meta.get("channel_name", "")),
            "platform":         str(video_meta.get("platform", "youtube")),
            "view_count":       int(video_meta.get("view_count") or 0),
            "like_count":       int(video_meta.get("like_count") or 0),
            "comment_count":    int(video_meta.get("comment_count") or 0),
            "engagement_rate":  float(video_meta.get("engagement_rate") or 0.0),
            "subscriber_count": int(video_meta.get("subscriber_count") or 0),
            "upload_date":      str(video_meta.get("upload_date") or ""),
        }
        for c in chunks
    ]

    col.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def similarity_search(
    query: str,
    k: int = 6,
    video_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    col = _get_collection()

    where = None
    if video_ids:
        if len(video_ids) == 1:
            where = {"video_id": {"$eq": video_ids[0]}}
        else:
            where = {"video_id": {"$in": video_ids}}

    total = col.count()
    if total == 0:
        return []

    kwargs: Dict[str, Any] = dict(
        query_texts=[query],
        n_results=min(k, total),
        include=["documents", "metadatas", "distances"],
    )
    if where:
        kwargs["where"] = where

    results = col.query(**kwargs)

    output = []
    docs  = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]

    for doc, meta, dist in zip(docs, metas, dists):
        output.append({
            "text":     doc,
            "metadata": meta,
            "score":    round(1 - dist, 4),
        })

    return output


def delete_video(video_id: str) -> int:
    col = _get_collection()
    try:
        existing = col.get(where={"video_id": {"$eq": video_id}})
        ids = existing.get("ids", [])
        if ids:
            col.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def collection_stats() -> Dict[str, Any]:
    col = _get_collection()
    total = col.count()
    stats: Dict[str, int] = {}

    for vid in ["A", "B"]:
        try:
            res = col.get(where={"video_id": {"$eq": vid}})
            stats[vid] = len(res.get("ids", []))
        except Exception:
            stats[vid] = 0

    return {"total": total, "per_video": stats}
