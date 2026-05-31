from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional

from services.transcript import fetch_transcript
from services.metadata    import fetch_metadata
from services.chunker     import chunk_transcript
from services.vectorstore import upsert_chunks, delete_video, collection_stats

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    url: str
    video_label: Literal["A", "B"]


class IngestResponse(BaseModel):
    video_id:         str
    video_label:      str
    platform:         str
    title:            str
    channel_name:     str
    chunks_stored:    int
    engagement_rate:  Optional[float]
    view_count:       Optional[int]
    like_count:       Optional[int]
    comment_count:    Optional[int]
    subscriber_count: Optional[int]
    duration_seconds: Optional[int]
    upload_date:      Optional[str]
    thumbnail_url:    Optional[str]
    tags:             list[str] = []


@router.post("", response_model=IngestResponse)
async def ingest_video(req: IngestRequest):
    try:
        segments = fetch_transcript(req.url)
        if not segments:
            raise HTTPException(400, "No transcript found for this video.")

        meta = fetch_metadata(req.url)
        delete_video(req.video_label)

        chunks = chunk_transcript(
            segments=segments,
            video_id=req.video_label,
            max_tokens=300,
            overlap_tokens=60,
        )

        if not chunks:
            raise HTTPException(500, "Chunking produced 0 chunks.")

        video_meta_dict = meta.dict_with_engagement()
        n = upsert_chunks(chunks, video_meta_dict)

        return IngestResponse(
            video_id=meta.video_id,
            video_label=req.video_label,
            platform=meta.platform,
            title=meta.title,
            channel_name=meta.channel_name,
            chunks_stored=n,
            engagement_rate=meta.engagement_rate,
            view_count=meta.view_count,
            like_count=meta.like_count,
            comment_count=meta.comment_count,
            subscriber_count=meta.subscriber_count,
            duration_seconds=meta.duration_seconds,
            upload_date=meta.upload_date,
            thumbnail_url=meta.thumbnail_url,
            tags=meta.tags[:10],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ingest failed: {e}") from e


@router.get("/status")
async def ingest_status():
    return collection_stats()
