function fmt(ms) {
  const s = Math.round(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
  const sec = String(s % 60).padStart(2, "0");
  return h > 0 ? h + ":" + m + ":" + sec : m + ":" + sec;
}

const pct = (part, whole) => (whole > 0 ? Math.round((part / whole) * 100) : 0);

export default function SessionSummary({ stats, running, onReset }) {
  const distracted = stats.awayMs + stats.closedMs;
  const attentive = Math.max(stats.monitoredMs - distracted, 0);
  const total = stats.monitoredMs;

  return (
    <section className="summary">
      <div className="summary-head">
        <h2>Session summary</h2>
        <button className="link-btn" onClick={onReset}>Reset</button>
      </div>
      <dl>
        <dt>Monitored time</dt>
        <dd>{fmt(total)}{running ? "" : " (paused)"}</dd>
        <dt>Attentive</dt>
        <dd>{fmt(attentive)} ({pct(attentive, total)}%)</dd>
        <dt>Distracted</dt>
        <dd>{fmt(distracted)} ({pct(distracted, total)}%)</dd>
        <dt>Looking away</dt>
        <dd>{stats.awayCount}x, {fmt(stats.awayMs)}</dd>
        <dt>Eyes closed</dt>
        <dd>{stats.closedCount}x, {fmt(stats.closedMs)}</dd>
        <dt>Longest distraction</dt>
        <dd>{fmt(stats.longestMs)}</dd>
      </dl>
    </section>
  );
}