
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List

from services.rag_agent import stream_answer

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str      
    content: str


class ChatRequest(BaseModel):
    question: str
    history: List[ChatMessage] = []


@router.post("/stream")
async def chat_stream(req: ChatRequest):
   
    history = [{"role": m.role, "content": m.content} for m in req.history]

    async def event_generator():
        try:
            async for event in stream_answer(req.question, history):
                yield event
        except Exception as e:
            import json
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
