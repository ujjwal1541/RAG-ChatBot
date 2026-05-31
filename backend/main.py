
from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers.ingest import router as ingest_router
from routers.chat   import router as chat_router

app = FastAPI(
    title="VidScan Engagement Intelligence API",
    version="1.0.0",
    description="RAG-powered video engagement analysis using LangGraph + ChromaDB",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "service": "VidScan API",
        "status": "running",
        "endpoints": {
            "ingest":        "POST /api/ingest",
            "ingest_status": "GET  /api/ingest/status",
            "chat_stream":   "POST /api/chat/stream",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
