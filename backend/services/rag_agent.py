
from __future__ import annotations
import os, json
from typing import AsyncIterator, List, Dict, Any, Optional, TypedDict, Annotated
import operator

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START

from services.vectorstore import similarity_search, collection_stats

load_dotenv()

_CHAT_MODEL = os.getenv("CHAT_MODEL", "meta/llama-3.1-70b-instruct")
_NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

_LLM = ChatOpenAI(
    model=_CHAT_MODEL,
    streaming=True,
    temperature=0.3,
    api_key=_NVIDIA_API_KEY,
    base_url="https://integrate.api.nvidia.com/v1",
)

SYSTEM_PROMPT = """You are an expert social media content analyst specializing in video engagement optimization. You help creators understand why videos perform differently and how to improve engagement.

You have access to transcript chunks and metadata from two videos:
- Video A and Video B (can be YouTube or Instagram Reels)

Engagement rate formula: (likes + comments) / views × 100

When answering:
1. Always cite which video and which chunk (with timestamp) your answer is based on.
2. Use exact numbers from metadata when available (views, likes, comments, engagement_rate, subscriber_count).
3. Be specific. If asked about the first 5 seconds (hook), quote from chunk with start_time near 0.
4. Format citations as [Video X | chunk N | t=Xs-Ys].
5. For comparisons, structure your answer with clear sections for each video.
6. Keep answers concise but data-rich.
7. When suggesting improvements, be concrete and actionable — specific words, techniques, CTAs.
8. For Instagram Reels, consider platform-specific factors: vertical format, audio/music, trending sounds, reels algorithm.
9. For YouTube, consider thumbnail, title SEO, watch time, click-through rate factors.

Context chunks retrieved from the vector DB will be injected before each question.
"""

NO_CHUNKS_PROMPT = """No transcript chunks have been indexed yet. Please ask the user to ingest both videos using the URL input panel before asking analysis questions."""


class AgentState(TypedDict):
    question:         str
    retrieved_chunks: List[Dict[str, Any]]
    chat_history:     Annotated[List, operator.add]
    answer:           str
    citations:        List[Dict[str, Any]]


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "[No chunks available — please ingest both videos first]"

    context_parts = []

    meta_seen: Dict[str, Dict] = {}
    for c in chunks:
        vid = c["metadata"]["video_id"]
        if vid not in meta_seen:
            meta_seen[vid] = c["metadata"]

    for vid, meta in sorted(meta_seen.items()):
        er = meta.get("engagement_rate", 0) or 0
        platform = meta.get("platform", "youtube")
        context_parts.append(
            f"[Video {vid} STATS] platform={platform} | title={meta.get('title','?')} | "
            f"channel={meta.get('channel_name','?')} | "
            f"subscribers/followers={meta.get('subscriber_count', 0):,} | "
            f"views={meta.get('view_count', 0):,} | "
            f"likes={meta.get('like_count', 0):,} | "
            f"comments={meta.get('comment_count', 0):,} | "
            f"engagement_rate={er:.4f}%"
        )

    context_parts.append("")
    for c in chunks:
        meta = c["metadata"]
        context_parts.append(
            f"[Video {meta['video_id']} | chunk {meta['chunk_index']} | "
            f"t={meta['start_time']}s-{meta['end_time']}s | score={c['score']}]\n"
            f"{c['text']}\n"
        )

    return "\n".join(context_parts)


def _build_citations(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "video_id":    c["metadata"]["video_id"],
            "chunk_index": c["metadata"]["chunk_index"],
            "start_time":  c["metadata"]["start_time"],
            "end_time":    c["metadata"]["end_time"],
            "score":       c["score"],
            "snippet":     c["text"][:120] + ("..." if len(c["text"]) > 120 else ""),
        }
        for c in chunks
    ]


def retrieve_node(state: AgentState) -> Dict[str, Any]:
    question  = state["question"]
    q_lower   = question.lower()
    video_filter = None

    if "video a" in q_lower and "video b" not in q_lower:
        video_filter = ["A"]
    elif "video b" in q_lower and "video a" not in q_lower:
        video_filter = ["B"]

    chunks = similarity_search(question, k=8, video_ids=video_filter)

    if any(kw in q_lower for kw in ["hook", "first 5", "opening", "intro", "start"]):
        hook_chunks = similarity_search(
            "opening hook first seconds introduction attention grab", k=4, video_ids=video_filter
        )
        seen_ids = {(c["metadata"]["video_id"], c["metadata"]["chunk_index"]) for c in chunks}
        for hc in hook_chunks:
            key = (hc["metadata"]["video_id"], hc["metadata"]["chunk_index"])
            if key not in seen_ids:
                chunks.append(hc)
                seen_ids.add(key)

    if any(kw in q_lower for kw in ["engagement", "rate", "views", "likes", "stats"]):
        if not video_filter:
            for vid in ["A", "B"]:
                vid_chunks = [c for c in chunks if c["metadata"]["video_id"] == vid]
                if not vid_chunks:
                    extra = similarity_search(question, k=2, video_ids=[vid])
                    chunks.extend(extra)

    return {"retrieved_chunks": chunks}


def generate_node(state: AgentState) -> Dict[str, Any]:
    chunks   = state["retrieved_chunks"]
    question = state["question"]
    history  = state.get("chat_history", [])

    context  = _build_context(chunks)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    for msg in history[-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=f"CONTEXT:\n{context}\n\nQUESTION: {question}"))

    response = _LLM.invoke(messages)
    return {"answer": response.content, "citations": _build_citations(chunks)}


def _build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)
    return builder.compile()


_graph = _build_graph()


async def stream_answer(
    question: str,
    chat_history: List[Dict[str, str]],
) -> AsyncIterator[str]:

    try:
       
        state: AgentState = {
            "question":         question,
            "retrieved_chunks": [],
            "chat_history":     chat_history,
            "answer":           "",
            "citations":        [],
        }

        retrieve_result = retrieve_node(state)
        state.update(retrieve_result)

        citations = _build_citations(state["retrieved_chunks"])
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

        chunks = state["retrieved_chunks"]

        if not chunks:
            stats = collection_stats()
            if stats.get("total", 0) == 0:
                error_msg = (
                    "No videos have been ingested yet. Please paste YouTube or Instagram URLs above "
                    "and click '⚡ Analyze Both' to load both videos first."
                )
            else:
                ingested = [v for v, c in stats.get("per_video", {}).items() if c > 0]
                if len(ingested) < 2:
                    missing = [v for v in ["A", "B"] if v not in ingested]
                    error_msg = (
                        f"Only Video {''.join(ingested)} has been ingested. "
                        f"Please also ingest Video {''.join(missing)} to enable comparisons."
                    )
                else:
                    error_msg = "No relevant chunks found for your question. Try rephrasing."

            full_answer = error_msg
            yield f"data: {json.dumps({'type': 'chunk', 'text': error_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'full_answer': full_answer})}\n\n"
            return

        context  = _build_context(chunks)
        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        for msg in chat_history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=f"CONTEXT:\n{context}\n\nQUESTION: {question}"))

        full_answer = ""
        async for token in _LLM.astream(messages):
            text = token.content
            if text:
                full_answer += text
                yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'full_answer': full_answer})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
