import { useEffect, useState } from "react";
import { getTimeline } from "../api.js";

export default function TimelinePanel() {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("idle");

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      setStatus("loading");
      try {
        const res = await getTimeline(80);
        if (mounted) {
          setEvents(res.events || []);
          setStatus("ready");
        }
      } catch (err) {
        if (mounted) setStatus(err.message || "failed");
      }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="timeline-panel">
      <div className="muted">Status: {status}</div>
      <div className="timeline">
        {events.length === 0 && <div className="muted">No events yet.</div>}
        {events.map((event) => (
          <div className="timeline-row" key={event.id}>
            <div className="timeline-dot" />
            <div className="timeline-content">
              <div className="timeline-title">
                {event.name || "Unknown"}{" "}
                <span className="timeline-sub">({event.face_type})</span>
              </div>
              <div className="timeline-meta">
                {event.event_type} · {event.created_at}
                {event.score !== null && event.score !== undefined && (
                  <span className="timeline-score">
                    score {event.score.toFixed(3)}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
