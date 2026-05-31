
from __future__ import annotations
from typing import List, Dict, Any
import tiktoken

TOKENIZER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(TOKENIZER.encode(text))


def chunk_transcript(
    segments: List[Dict[str, Any]],
    video_id: str,
    max_tokens: int = 300,
    overlap_tokens: int = 60,
) -> List[Dict[str, Any]]:
   
    chunks: List[Dict[str, Any]] = []

    words: List[Dict[str, Any]] = []
    for seg in segments:
        seg_words = seg["text"].split()
        if not seg_words:
            continue
        dur_per_word = seg["duration"] / max(len(seg_words), 1)
        for i, w in enumerate(seg_words):
            words.append({
                "word":  w,
                "start": seg["start"] + i * dur_per_word,
                "end":   seg["start"] + (i + 1) * dur_per_word,
            })

    if not words:
        return []

    cursor    = 0
    chunk_idx = 0

    while cursor < len(words):
        buf:        List[str] = []
        buf_tokens = 0
        start_word = cursor
        i          = cursor

        while i < len(words):
            tok = _count_tokens(words[i]["word"])
            if buf_tokens + tok > max_tokens and buf:
                break
            buf.append(words[i]["word"])
            buf_tokens += tok
            i += 1

        text = " ".join(buf)
        chunks.append({
            "chunk_id":    f"{video_id}_chunk_{chunk_idx:04d}",
            "video_id":    video_id,
            "chunk_index": chunk_idx,
            "text":        text,
            "token_count": buf_tokens,
            "start_time":  round(words[start_word]["start"], 2),
            "end_time":    round(words[i - 1]["end"], 2),
        })

        chunk_idx += 1
        overlap_buf = 0
        back = i - 1
        while back > cursor and overlap_buf < overlap_tokens:
            overlap_buf += _count_tokens(words[back]["word"])
            back -= 1
        cursor = max(back + 1, cursor + 1)  

    return chunks
