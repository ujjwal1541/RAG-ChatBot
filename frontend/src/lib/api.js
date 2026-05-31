/**
 * lib/api.js
 * ──────────
 * All communication with the FastAPI backend.
 * During dev, Vite proxies /api → http://localhost:8000
 * In production, set VITE_API_BASE to your deployed URL.
 */

const BASE = import.meta.env.VITE_API_BASE || "";

/**
 * Ingest a video URL into the vector store.
 * @param {string} url         - YouTube or Instagram URL
 * @param {"A"|"B"} videoLabel - Which slot to use
 * @returns {Promise<IngestResponse>}
 */
export async function ingestVideo(url, videoLabel) {
  const res = await fetch(`${BASE}/api/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, video_label: videoLabel }),
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail || body.message || msg;
    } catch (_) {}
    throw new Error(msg);
  }

  return res.json();
}

/**
 * Stream a chat response via SSE.
 * @param {string}   question  - User question
 * @param {Array}    history   - [{role, content}, ...]
 * @param {Function} onEvent   - Called for each parsed SSE event
 * @param {Function} onAbort   - Receives a cancel() function
 */
export async function streamChat(question, history, onEvent, onAbort) {
  const controller = new AbortController();
  if (onAbort) onAbort(() => controller.abort());

  const res = await fetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
    signal: controller.signal,
  });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      msg = body.detail || body.message || msg;
    } catch (_) {}
    throw new Error(msg);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events are delimited by double newlines
    const parts = buffer.split("\n\n");
    buffer = parts.pop(); // hold incomplete last part

    for (const part of parts) {
      const line = part.trim();
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6));
          onEvent(event);
        } catch (_) {}
      }
    }
  }

  // Flush any remaining buffer
  if (buffer.trim().startsWith("data: ")) {
    try {
      const event = JSON.parse(buffer.trim().slice(6));
      onEvent(event);
    } catch (_) {}
  }
}

/**
 * Get current ingest status from the backend.
 */
export async function getIngestStatus() {
  const res = await fetch(`${BASE}/api/ingest/status`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
