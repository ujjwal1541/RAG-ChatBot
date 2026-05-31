import { useMemo } from "react";

function fmt(n) {
  if (!n && n !== 0) return "—";
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

function fmtDate(d) {
  if (!d) return "—";
  if (/^\d{8}$/.test(d)) {
    return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
  }
  return d;
}

function fmtDuration(s) {
  if (!s) return "—";
  const m   = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

export function VideoPanel({ label, data, status }) {
  const engagementColor = useMemo(() => {
    if (!data?.engagement_rate) return "";
    const r = data.engagement_rate;
    if (r >= 5) return "engage--hot";
    if (r >= 2) return "engage--warm";
    return "engage--cool";
  }, [data?.engagement_rate]);

  const isInstagram = data?.platform === "instagram";

  return (
    <div
      className={`video-panel video-panel--${label.toLowerCase()} ${
        status === "loading" ? "video-panel--loading" : ""
      }`}
    >
      <div className="panel-label">
        <span className="panel-badge">VIDEO {label}</span>
        {data?.platform && (
          <span className={`panel-platform panel-platform--${data.platform}`}>
            {isInstagram ? "📷 Reel" : "▶ YouTube"}
          </span>
        )}
      </div>

      {/* ── Loading skeleton ── */}
      {status === "loading" && (
        <div className="panel-skeleton">
          <div className="skeleton-thumb" />
          <div className="skeleton-lines">
            <div className="skeleton-line skeleton-line--lg" />
            <div className="skeleton-line skeleton-line--sm" />
            <div className="skeleton-line skeleton-line--md" />
          </div>
          <div className="skeleton-stats">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="skeleton-stat" />
            ))}
          </div>
        </div>
      )}

      {/* ── Empty idle ── */}
      {status === "idle" && !data && (
        <div className="panel-empty">
          <div className="empty-icon">◻</div>
          <p className="empty-text">Paste a YouTube or Instagram URL to analyze Video {label}</p>
        </div>
      )}

      {/* ── Error ── */}
      {status === "error" && (
        <div className="panel-empty panel-empty--error">
          <div className="empty-icon">✕</div>
          <p className="empty-text">Ingest failed — check the URL and try again</p>
        </div>
      )}

      {/* ── Loaded data ── */}
      {data && status !== "loading" && (
        <div className="panel-content">
          {data.thumbnail_url && (
            <div className={`thumb-wrap ${isInstagram ? "thumb-wrap--reel" : ""}`}>
              <img
                className="thumb"
                src={data.thumbnail_url}
                alt={data.title}
                loading="lazy"
              />
              {data.duration_seconds && (
                <span className="thumb-duration">
                  {fmtDuration(data.duration_seconds)}
                </span>
              )}
            </div>
          )}

          <div className="panel-info">
            <h3 className="video-title" title={data.title}>
              {data.title}
            </h3>

            <div className="video-channel">
              <span className="channel-icon">{isInstagram ? "📷" : "◉"}</span>
              <span>{data.channel_name}</span>
              {data.subscriber_count > 0 && (
                <span className="sub-count">
                  {fmt(data.subscriber_count)} {isInstagram ? "followers" : "subs"}
                </span>
              )}
            </div>

            <div className="video-stats">
              <StatChip icon="👁"  label="Views"    value={fmt(data.view_count)}    />
              <StatChip icon="♥"  label="Likes"    value={fmt(data.like_count)}    />
              <StatChip icon="💬" label="Comments" value={fmt(data.comment_count)} />
              <StatChip icon="📅" label="Uploaded" value={fmtDate(data.upload_date)} />
            </div>

            <div className={`engagement-rate ${engagementColor}`}>
              <span className="er-label">Engagement Rate</span>
              <span className="er-value">
                {data.engagement_rate != null
                  ? `${data.engagement_rate.toFixed(3)}%`
                  : "—"}
              </span>
              <EngagementBar rate={data.engagement_rate} />
            </div>

            {data.tags && data.tags.length > 0 && (
              <div className="tags">
                {data.tags.slice(0, 8).map((t, i) => (
                  <span key={i} className="tag">
                    #{t}
                  </span>
                ))}
              </div>
            )}

            <div className="chunks-badge">
              <span className="chunks-icon">⬡</span>
              <span>{data.chunks_stored} chunks indexed</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatChip({ icon, label, value }) {
  return (
    <div className="stat-chip">
      <span className="stat-icon">{icon}</span>
      <div className="stat-inner">
        <span className="stat-value">{value}</span>
        <span className="stat-label">{label}</span>
      </div>
    </div>
  );
}

function EngagementBar({ rate }) {
  const pct = Math.min(((rate || 0) / 10) * 100, 100);
  return (
    <div className="er-bar-bg">
      <div className="er-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}
