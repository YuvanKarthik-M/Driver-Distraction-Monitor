const LABELS = { looking_away: "Looking away", drowsy: "Eyes closed" };

export default function EventLog({ events }) {
  return (
    <section className="log">
      <h2>Event log</h2>
      {events.length === 0 ? (
        <p className="muted">No distraction events yet.</p>
      ) : (
        <table>
          <tbody>
            {events.map((e, i) => (
              <tr key={i}>
                <td>{e.time}</td>
                <td>{LABELS[e.status]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
