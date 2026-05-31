
from __future__ import annotations
import subprocess, json, re
from typing import Optional, List
from pydantic import BaseModel


class VideoMeta(BaseModel):
    video_id: str
    platform: str = "youtube"        
    title: str
    channel_name: str
    subscriber_count: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    duration_seconds: Optional[int] = None
    upload_date: Optional[str] = None         
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []

    @property
    def engagement_rate(self) -> Optional[float]:
        if self.view_count and self.view_count > 0:
            likes    = self.like_count    or 0
            comments = self.comment_count or 0
            return round((likes + comments) / self.view_count * 100, 4)
        return None

    def dict_with_engagement(self) -> dict:
        d = self.model_dump()
        d["engagement_rate"] = self.engagement_rate
        return d


def _extract_youtube_id(url_or_id: str) -> str:
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract video ID from: {url_or_id!r}")


def _extract_instagram_shortcode(url: str) -> str:
    m = re.search(r"/(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    return url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]


def _fetch_via_ytdlp(url: str) -> dict:
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-playlist", url],
        capture_output=True, text=True, timeout=45
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return json.loads(result.stdout)


def fetch_metadata(url_or_id: str) -> VideoMeta:

    is_instagram = "instagram.com" in url_or_id or "instagr.am" in url_or_id

    if is_instagram:
        return _fetch_instagram_metadata(url_or_id)
    else:
        return _fetch_youtube_metadata(url_or_id)


def _fetch_youtube_metadata(url_or_id: str) -> VideoMeta:

    video_id = _extract_youtube_id(url_or_id)
    url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        info = _fetch_via_ytdlp(url)

        return VideoMeta(
            video_id=video_id,
            platform="youtube",
            title=info.get("title", "Unknown Title"),
            channel_name=info.get("uploader") or info.get("channel", "Unknown Channel"),
            subscriber_count=info.get("channel_follower_count"),
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            comment_count=info.get("comment_count"),
            duration_seconds=info.get("duration"),
            upload_date=info.get("upload_date"),
            thumbnail_url=info.get("thumbnail"),
            description=(info.get("description") or "")[:2000],
            tags=info.get("tags") or [],
        )

    except FileNotFoundError:
        return VideoMeta(
            video_id=video_id,
            platform="youtube",
            title=f"Video {video_id}",
            channel_name="Unknown (yt-dlp not installed)",
        )
    except Exception as e:
        return VideoMeta(
            video_id=video_id,
            platform="youtube",
            title=f"Video {video_id}",
            channel_name=f"Metadata fetch error: {str(e)[:100]}",
        )


def _fetch_instagram_metadata(url: str) -> VideoMeta:
    shortcode = _extract_instagram_shortcode(url)

    try:
        info = _fetch_via_ytdlp(url)

        uploader = info.get("uploader") or info.get("uploader_id") or info.get("channel", "Unknown Creator")
        title = info.get("title") or info.get("description", "")
        if not title:
            title = f"Instagram Reel by @{uploader}"
        if len(title) > 100:
            title = title[:97] + "..."

        follower_count = info.get("channel_follower_count") or info.get("uploader_follower_count")

        desc = info.get("description") or ""
        hashtags = re.findall(r"#(\w+)", desc)

        return VideoMeta(
            video_id=shortcode,
            platform="instagram",
            title=title,
            channel_name=uploader,
            subscriber_count=follower_count,
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            comment_count=info.get("comment_count"),
            duration_seconds=info.get("duration"),
            upload_date=info.get("upload_date"),
            thumbnail_url=info.get("thumbnail"),
            description=desc[:2000],
            tags=hashtags[:20],
        )

    except FileNotFoundError:
        return VideoMeta(
            video_id=shortcode,
            platform="instagram",
            title=f"Instagram Reel {shortcode}",
            channel_name="Unknown (yt-dlp not installed)",
        )
    except Exception as e:
        return VideoMeta(
            video_id=shortcode,
            platform="instagram",
            title=f"Instagram Reel {shortcode}",
            channel_name=f"Metadata unavailable: {str(e)[:80]}",
            description="Instagram may require authentication. Public reels should work with yt-dlp.",
        )
