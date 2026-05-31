import { useState, useCallback } from "react";
import { VideoPanel } from "./components/VideoPanel";
import { ChatPanel } from "./components/ChatPanel";
import { IngestBar } from "./components/IngestBar";
import { StatusBadge } from "./components/StatusBadge";

export default function App() {
  const [videoA, setVideoA] = useState(null);
  const [videoB, setVideoB] = useState(null);
  const [ingestStatus, setIngestStatus] = useState({ A: "idle", B: "idle" });

  const handleIngestComplete = useCallback((label, data) => {
    if (label === "A") setVideoA(data);
    if (label === "B") setVideoB(data);
    setIngestStatus((s) => ({ ...s, [label]: "done" }));
  }, []);

  const handleIngestStart = useCallback((label) => {
    setIngestStatus((s) => ({ ...s, [label]: "loading" }));
  }, []);

  const handleIngestError = useCallback((label) => {
    setIngestStatus((s) => ({ ...s, [label]: "error" }));
  }, []);

  const bothReady = !!videoA && !!videoB;

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo-area">
            <span className="logo-mark">▶</span>
            <span className="logo-text">VIDSCAN</span>
            <span className="logo-sub">engagement intelligence</span>
          </div>
          <div className="header-badges">
            <StatusBadge label="A" status={ingestStatus.A} meta={videoA} />
            <StatusBadge label="B" status={ingestStatus.B} meta={videoB} />
          </div>
        </div>
      </header>

      <main className="main">
        <section className="ingest-section">
          <IngestBar
            onIngestStart={handleIngestStart}
            onIngestComplete={handleIngestComplete}
            onIngestError={handleIngestError}
          />
        </section>

        <section className="videos-section">
          <VideoPanel label="A" data={videoA} status={ingestStatus.A} />
          <div className="vs-divider">
            <span className="vs-text">VS</span>
          </div>
          <VideoPanel label="B" data={videoB} status={ingestStatus.B} />
        </section>

        <section className="chat-section">
          <ChatPanel ready={bothReady} videoA={videoA} videoB={videoB} />
        </section>
      </main>
    </div>
  );
}
