const LABELS = {
  ok: "Attentive",
  looking_away: "Looking away",
  drowsy: "Eyes closed",
  phone: "Using phone",
};

export default function StatusPanel({ data, connected, paused }) {
  let label = "Connecting to the backend…";
  let tone = "idle";
  if (paused) {
    label = "Monitoring stopped";
  } else if (connected && data) {
    if (data.calibrating) {
      label = "Calibrating: look straight ahead";
    } else {
      label = LABELS[data.status];
      tone = data.status === "ok" ? "ok" : "bad";
    }
  }

  return (
    <section className="panel">
      <p className={"status " + tone}>{label}</p>
      <dl>
        <dt>Head turn (yaw)</dt>
        <dd>{data ? data.yaw + "°" : "-"}</dd>
        <dt>Head tilt (pitch)</dt>
        <dd>{data ? data.pitch + "°" : "-"}</dd>
        <dt>Eye openness (EAR)</dt>
        <dd>{data ? data.ear : "-"}</dd>
        <dt>Backend</dt>
        <dd>{connected ? "Connected" : "Reconnecting…"}</dd>
      </dl>
    </section>
  );
}