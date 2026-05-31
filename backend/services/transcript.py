
from __future__ import annotations
import json, re, subprocess, tempfile, os
from pathlib import Path
from typing import List, Dict, Any

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


def detect_platform(url: str) -> str:
    if "instagram.com" in url or "instagr.am" in url:
        return "instagram"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    return "unknown"


def _extract_video_id(url_or_id: str) -> str:
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract YouTube video ID from: {url_or_id!r}")


def _parse_vtt(vtt_text: str) -> List[Dict[str, Any]]:
    segments = []
    blocks = re.split(r"\n\n+", vtt_text.strip())
    time_re = re.compile(
        r"(\d{2}:\d{2}:\d{2}\.\d{3})\s-->\s(\d{2}:\d{2}:\d{2}\.\d{3})"
    )

    def to_sec(ts: str) -> float:
        h, m, s = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    for block in blocks:
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            m = time_re.match(line)
            if m:
                start = to_sec(m.group(1))
                end   = to_sec(m.group(2))
                text  = " ".join(
                    re.sub(r"<[^>]+>", "", l)
                    for l in lines[i + 1:]
                    if l and not re.match(r"^\d+$", l)
                ).strip()
                if text:
                    segments.append({"text": text, "start": start, "duration": end - start})
                break
    return segments



def _fetch_via_ytdlp(url: str) -> List[Dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "--no-check-certificates",
            "--compat-options", "no-youtube-unavailable-videos",
            "--output", os.path.join(tmpdir, "%(id)s.%(ext)s"),
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        vtt_files = list(Path(tmpdir).glob("*.vtt"))
        if vtt_files:
            return _parse_vtt(vtt_files[0].read_text(encoding="utf-8"))
        raise RuntimeError(result.stderr[-300:])
    
def _fetch_instagram_transcript(url: str) -> List[Dict[str, Any]]:

    nvidia_key = os.getenv("NVIDIA_API_KEY", "")

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "reel_audio.mp3")
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",   
            "--output", audio_path,
            "--no-playlist",
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        audio_files = list(Path(tmpdir).glob("*.mp3")) + list(Path(tmpdir).glob("*.m4a"))

        if not audio_files:
            return [{"text": "Instagram Reel transcript unavailable. Audio could not be extracted.", "start": 0.0, "duration": 30.0}]

        audio_file = audio_files[0]
        if nvidia_key:
            try:
                from openai import OpenAI
                client = OpenAI(
                    api_key=nvidia_key,
                    base_url="https://integrate.api.nvidia.com/v1",
                )
                with open(audio_file, "rb") as f:
                    response = client.audio.transcriptions.create(
                        model="openai/whisper-large-v3",
                        file=f,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                    )

                segments = []
                for seg in response.segments:
                    segments.append({
                        "text": seg.text.strip(),
                        "start": seg.start,
                        "duration": seg.end - seg.start,
                    })

                return segments if segments else [{"text": response.text, "start": 0.0, "duration": 30.0}]

            except Exception as e:
                return [{"text": f"Transcription failed: {e}. Please check your NVIDIA_API_KEY.", "start": 0.0, "duration": 30.0}]
        else:
            return [{"text": "Instagram Reel: NVIDIA_API_KEY required for audio transcription. Set NVIDIA_API_KEY in .env.", "start": 0.0, "duration": 30.0}]

def _fetch_via_requests(video_id: str) -> List[Dict[str, Any]]:
    import urllib.request
    import xml.etree.ElementTree as ET

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    page_url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(page_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    match = re.search(r'"captionTracks":\[(\{.*?\})\]', html)
    if not match:
        raise RuntimeError("No caption tracks found in page source")

    import json as _json
    track_json = "[" + match.group(1) + "]"
    tracks = _json.loads(track_json)

    base_url = None
    for track in tracks:
        lang = track.get("languageCode", "")
        if lang.startswith("en"):
            base_url = track.get("baseUrl")
            break
    if not base_url and tracks:
        base_url = tracks[0].get("baseUrl")
    if not base_url:
        raise RuntimeError("No usable caption track URL found")

    req2 = urllib.request.Request(base_url, headers=headers)
    with urllib.request.urlopen(req2, timeout=15) as resp:
        xml_data = resp.read().decode("utf-8", errors="ignore")

    root = ET.fromstring(xml_data)
    segments = []
    for el in root.findall(".//text"):
        start = float(el.get("start", 0))
        dur   = float(el.get("dur", 2))
        text  = (el.text or "").strip()
        text  = re.sub(r"<[^>]+>", "", text)
        text  = text.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
        if text:
            segments.append({"text": text, "start": start, "duration": dur})
    return segments

def fetch_transcript(url_or_id: str) -> List[Dict[str, Any]]:
    platform = detect_platform(url_or_id)
    if platform == "instagram":
        return _fetch_instagram_transcript(url_or_id)

    video_id = _extract_video_id(url_or_id)
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        for lang in ["en", "en-US", "en-GB", "en-IN"]:
            try:
                t = transcript_list.find_manually_created_transcript([lang])
                segs = t.fetch()
                return [{"text": s["text"], "start": s["start"], "duration": s["duration"]} for s in segs]
            except Exception:
                pass

        for lang in ["en", "en-US", "en-GB", "en-IN"]:
            try:
                t = transcript_list.find_generated_transcript([lang])
                segs = t.fetch()
                return [{"text": s["text"], "start": s["start"], "duration": s["duration"]} for s in segs]
            except Exception:
                pass

        for t in transcript_list:
            try:
                segs = t.fetch()
                return [{"text": s["text"], "start": s["start"], "duration": s["duration"]} for s in segs]
            except Exception:
                continue

    except Exception:
        pass

    try:
        return _fetch_via_ytdlp(f"https://www.youtube.com/watch?v={video_id}")
    except Exception as e:
        raise RuntimeError(
            f"All transcript methods failed for {video_id}. "
            f"Try a different video or check if it has captions enabled. Last error: {e}"
        ) from e
    try:
        return _fetch_via_requests(video_id)
    except Exception as e:
        raise RuntimeError(
            f"All transcript methods failed for {video_id}. "
            f"Make sure the video has captions enabled. Last error: {e}"
        ) from e

def full_text(segments: List[Dict[str, Any]]) -> str:
    return " ".join(s["text"] for s in segments)
