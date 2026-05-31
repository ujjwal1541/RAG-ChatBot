import { useState, useRef, useEffect, useCallback } from "react";
import { streamChat } from "../lib/api";

const SUGGESTIONS = [
  "Why did Video A get more engagement than Video B?",
  "What's the engagement rate of each video?",
  "Compare the hooks in the first 5 seconds.",
  "Who's the creator of Video B and what's their follower count?",
  "Suggest improvements for B based on what worked in A.",
];

export function ChatPanel({ ready, videoA, videoB }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [citations, setCitations] = useState([]);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const buildHistory = useCallback(() => {
    return messages
      .filter((m) => m.role !== "system" && !m.streaming)
      .map((m) => ({ role: m.role, content: m.text }));
  }, [messages]);

  const sendMessage = useCallback(async (text) => {
    const question = (text !== undefined ? text : input).trim();
    if (!question || streaming || !ready) return;

    setInput("");
    setCitations([]);

    const userMsg = { id: Date.now(), role: "user", text: question };
    const assistantId = Date.now() + 1;

    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: "assistant", text: "", streaming: true },
    ]);
    setStreaming(true);

    const history = buildHistory();

    try {
      let fullText = "";

      await streamChat(
        question,
        history,
        (event) => {
          if (event.type === "citations") {
            setCitations(event.citations || []);
          } else if (event.type === "chunk") {
            fullText += event.text;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, text: fullText, streaming: true }
                  : m
              )
            );
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, text: event.full_answer || fullText, streaming: false }
                  : m
              )
            );
          } else if (event.type === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, text: `⚠ Error: ${event.message}`, streaming: false, error: true }
                  : m
              )
            );
          }
        },
        (abort) => { abortRef.current = abort; }
      );
    } catch (e) {
      if (e.name !== "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, text: `⚠ ${e.message}`, streaming: false, error: true }
              : m
          )
        );
      }
    } finally {
      setStreaming(false);
    }
  }, [input, streaming, ready, buildHistory]);

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function clearChat() {
    setMessages([]);
    setCitations([]);
    if (abortRef.current) abortRef.current();
  }

  function stopStreaming() {
    if (abortRef.current) {
      abortRef.current();
      setStreaming(false);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-step">02</span>
        <span className="chat-title">RAG Analysis Chat</span>
        <div className="chat-header-meta">
          {ready ? (
            <span className="ready-pill">● READY</span>
          ) : (
            <span className="notready-pill">○ Ingest both videos first</span>
          )}
          {messages.length > 0 && (
            <button className="btn-clear" onClick={clearChat} title="Clear chat">
              ✕ Clear
            </button>
          )}
        </div>
      </div>

      <div className="chat-body">
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-icon">◈</div>
            <p className="chat-empty-text">
              {ready
                ? "Ask anything about Video A vs Video B"
                : "Load both videos above to start the analysis"}
            </p>
            {ready && (
              <div className="suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    className="suggestion-btn"
                    onClick={() => sendMessage(s)}
                    disabled={streaming}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((m) => (
          <MessageBubble key={m.id} msg={m} />
        ))}

        {citations.length > 0 && streaming && (
          <CitationsPanel citations={citations} />
        )}

        {!streaming && citations.length > 0 && (
          <CitationsPanel citations={citations} />
        )}

        <div ref={bottomRef} />
      </div>

      <div className="chat-footer">
        <div className={`chat-input-wrap ${!ready ? "chat-input-wrap--disabled" : ""}`}>
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={ready ? "Ask about engagement, hooks, improvements... (Enter to send)" : "Ingest both videos first"}
            disabled={!ready || streaming}
            rows={1}
          />
          {streaming ? (
            <button className="btn-stop" onClick={stopStreaming} title="Stop generating">
              ■
            </button>
          ) : (
            <button
              className="btn-send"
              onClick={() => sendMessage()}
              disabled={!ready || !input.trim()}
            >
              ↑
            </button>
          )}
        </div>
        {streaming && (
          <div className="streaming-indicator">
            <span className="stream-dot" /><span className="stream-dot" /><span className="stream-dot" />
            <span className="stream-label">Generating response...</span>
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`message-wrap ${isUser ? "message-wrap--user" : "message-wrap--assistant"}`}>
      <div className={`message-avatar ${isUser ? "avatar--user" : "avatar--assistant"}`}>
        {isUser ? "U" : "AI"}
      </div>
      <div className={`message-bubble ${msg.error ? "message-bubble--error" : ""}`}>
        <MessageContent text={msg.text} />
        {msg.streaming && <span className="cursor-blink">▌</span>}
      </div>
    </div>
  );
}

function MessageContent({ text }) {
  if (!text) return null;

  const lines = text.split("\n");
  const elements = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(<ul key={`ul-${elements.length}`} className="msg-ul">{listItems}</ul>);
      listItems = [];
    }
  };

  lines.forEach((line, i) => {
    if (line.startsWith("### ")) {
      flushList();
      elements.push(<h4 key={i} className="msg-h4">{inlineFormat(line.slice(4))}</h4>);
    } else if (line.startsWith("## ")) {
      flushList();
      elements.push(<h3 key={i} className="msg-h3">{inlineFormat(line.slice(3))}</h3>);
    } else if (line.startsWith("# ")) {
      flushList();
      elements.push(<h2 key={i} className="msg-h2">{inlineFormat(line.slice(2))}</h2>);
    } else if (line.match(/^[-*] /)) {
      listItems.push(<li key={i} className="msg-li">{inlineFormat(line.slice(2))}</li>);
    } else if (line.match(/^\d+\. /)) {
      flushList();
      elements.push(<p key={i} className="msg-numbered">{inlineFormat(line)}</p>);
    } else if (line.trim() === "") {
      flushList();
      elements.push(<div key={i} className="msg-spacer" />);
    } else {
      flushList();
      elements.push(<p key={i} className="msg-p">{inlineFormat(line)}</p>);
    }
  });

  flushList();

  return <div className="message-text">{elements}</div>;
}

function inlineFormat(text) {
  const segments = [];
  const citationRe = /\[Video ([AB])[^\]]+\]/g;
  let lastIndex = 0;
  let match;
  citationRe.lastIndex = 0;

  while ((match = citationRe.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", content: text.slice(lastIndex, match.index) });
    }
    segments.push({ type: "citation", content: match[0], video: match[1] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    segments.push({ type: "text", content: text.slice(lastIndex) });
  }
  if (segments.length === 0) {
    segments.push({ type: "text", content: text });
  }

  return segments.map((seg, i) => {
    if (seg.type === "citation") {
      return (
        <span key={i} className={`inline-cite inline-cite--${seg.video.toLowerCase()}`}>
          {seg.content}
        </span>
      );
    }
    // Process bold and inline code
    const parts = seg.content.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return parts.map((p, j) => {
      if (p.startsWith("**") && p.endsWith("**")) {
        return <strong key={`${i}-${j}`}>{p.slice(2, -2)}</strong>;
      }
      if (p.startsWith("`") && p.endsWith("`")) {
        return <code key={`${i}-${j}`} className="msg-code">{p.slice(1, -1)}</code>;
      }
      return p;
    });
  });
}

function CitationsPanel({ citations }) {
  const [open, setOpen] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="citations-panel">
      <button className="citations-toggle" onClick={() => setOpen((o) => !o)}>
        <span className="cite-icon">◎</span>
        {citations.length} source{citations.length > 1 ? "s" : ""} retrieved
        <span className="cite-arrow">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="citations-list">
          {citations.map((c, i) => (
            <div key={i} className={`citation-item citation-item--${c.video_id.toLowerCase()}`}>
              <div className="citation-header">
                <span className="citation-vid">Video {c.video_id}</span>
                <span className="citation-chunk">chunk #{c.chunk_index}</span>
                <span className="citation-time">t={c.start_time}s–{c.end_time}s</span>
                <span className="citation-score">↑{(c.score * 100).toFixed(0)}%</span>
              </div>
              <p className="citation-snippet">{c.snippet}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
