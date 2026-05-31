import { useState } from "react";
import { ingestVideo } from "../lib/api";

export function IngestBar({ onIngestStart, onIngestComplete, onIngestError }) {
  const [urlA, setUrlA] = useState("");
  const [urlB, setUrlB] = useState("");
  const [loadingA, setLoadingA] = useState(false);
  const [loadingB, setLoadingB] = useState(false);
  const [errorA, setErrorA] = useState("");
  const [errorB, setErrorB] = useState("");

  async function handleIngest(label, url, setLoading, setError) {
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Paste a YouTube or Instagram Reels URL");
      return;
    }
    setError("");
    setLoading(true);
    onIngestStart(label);
    try {
      const data = await ingestVideo(trimmed, label);
      onIngestComplete(label, data);
    } catch (e) {
      setError(e.message || "Ingest failed");
      onIngestError(label);
    } finally {
      setLoading(false);
    }
  }

  async function handleIngestBoth() {
    const promises = [];
    if (urlA.trim()) {
      setErrorA("");
      setLoadingA(true);
      onIngestStart("A");
      promises.push(
        ingestVideo(urlA.trim(), "A")
          .then((d) => { onIngestComplete("A", d); setLoadingA(false); })
          .catch((e) => { setErrorA(e.message); onIngestError("A"); setLoadingA(false); })
      );
    }
    if (urlB.trim()) {
      setErrorB("");
      setLoadingB(true);
      onIngestStart("B");
      promises.push(
        ingestVideo(urlB.trim(), "B")
          .then((d) => { onIngestComplete("B", d); setLoadingB(false); })
          .catch((e) => { setErrorB(e.message); onIngestError("B"); setLoadingB(false); })
      );
    }
    await Promise.all(promises);
  }

  const bothLoading = loadingA || loadingB;
  const neitherHasUrl = !urlA.trim() && !urlB.trim();

  return (
    <div className="ingest-bar">
      <div className="ingest-title">
        <span className="ingest-step">01</span>
        <span>Load Videos</span>
        <span className="ingest-hint">YouTube or Instagram Reels</span>
      </div>
      <div className="ingest-inputs">
        <UrlInput
          label="A"
          value={urlA}
          onChange={setUrlA}
          loading={loadingA}
          error={errorA}
          onSubmit={() => handleIngest("A", urlA, setLoadingA, setErrorA)}
          placeholder="youtube.com/watch?v=... or instagram.com/reel/..."
        />
        <UrlInput
          label="B"
          value={urlB}
          onChange={setUrlB}
          loading={loadingB}
          error={errorB}
          onSubmit={() => handleIngest("B", urlB, setLoadingB, setErrorB)}
          placeholder="youtube.com/watch?v=... or instagram.com/reel/..."
        />
      </div>
      <button
        className="btn-ingest-both"
        onClick={handleIngestBoth}
        disabled={neitherHasUrl || bothLoading}
      >
        {bothLoading ? (
          <><span className="spinner" /> Ingesting...</>
        ) : (
          "⚡ Analyze Both"
        )}
      </button>
    </div>
  );
}

function detectPlatform(url) {
  if (!url) return null;
  if (url.includes("instagram.com") || url.includes("instagr.am")) return "instagram";
  if (url.includes("youtube.com") || url.includes("youtu.be")) return "youtube";
  return null;
}

function UrlInput({ label, value, onChange, loading, error, onSubmit, placeholder }) {
  const platform = detectPlatform(value);

  function handleKey(e) {
    if (e.key === "Enter") onSubmit();
  }

  return (
    <div className="url-input-group">
      <label className="url-label">
        Video {label}
        {platform && (
          <span className={`platform-tag platform-tag--${platform}`}>
            {platform === "youtube" ? "▶ YouTube" : "📷 Instagram"}
          </span>
        )}
      </label>
      <div className="url-input-row">
        <input
          className={`url-input ${error ? "url-input--error" : ""}`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          placeholder={placeholder}
          disabled={loading}
          spellCheck={false}
        />
        <button
          className="btn-ingest-single"
          onClick={onSubmit}
          disabled={loading || !value.trim()}
        >
          {loading ? <span className="spinner spinner--sm" /> : "↗"}
        </button>
      </div>
      {error && <span className="url-error">{error}</span>}
    </div>
  );
}
