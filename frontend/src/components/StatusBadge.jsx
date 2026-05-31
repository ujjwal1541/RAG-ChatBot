export function StatusBadge({ label, status, meta }) {
  const icons = {
    idle:    "○",
    loading: "◌",
    done:    "●",
    error:   "✕",
  };
  const icon = icons[status] || "○";
  const platformIcon = meta?.platform === "instagram" ? "📷" : "▶";

  return (
    <div className={`status-badge status-badge--${status}`}>
      <span className="status-icon">{icon}</span>
      <span className="status-label">
        {meta?.platform === "instagram" ? "📷" : ""} Video {label}
      </span>
      {meta && status === "done" && (
        <span className="status-er">
          {meta.engagement_rate != null
            ? `${meta.engagement_rate.toFixed(2)}%`
            : "—"}
        </span>
      )}
    </div>
  );
}
