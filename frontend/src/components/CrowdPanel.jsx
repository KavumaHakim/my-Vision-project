import { useEffect, useState } from "react";
import { getCrowdLast } from "../api.js";

function riskClass(level) {
  if (level === "high") return "crowd-risk high";
  if (level === "elevated") return "crowd-risk elevated";
  if (level === "watch") return "crowd-risk watch";
  return "crowd-risk";
}

export default function CrowdPanel() {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const data = await getCrowdLast();
        if (!mounted) return;
        setPayload(data?.result || null);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err.message || "crowd_fetch_failed");
      }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const people = payload?.people || {};
  const crowd = payload?.crowd || {};
  const behavior = payload?.behavior || {};
  const objectCounts = payload?.objects?.counts || {};
  const objectSummary = Object.entries(objectCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="crowd-panel">
      {!payload && !error && <div className="muted">Waiting for crowd analytics...</div>}

      {payload && (
        <>
          <div className="crowd-top">
            <div className="crowd-stat">
              <span>People Estimate</span>
              <strong>{people.estimate ?? 0}</strong>
            </div>
            <div className="crowd-stat">
              <span>Crowd Level</span>
              <strong>{crowd.level || "none"}</strong>
            </div>
            <div className="crowd-stat">
              <span>Occupancy</span>
              <strong>{((crowd.occupancy_ratio || 0) * 100).toFixed(1)}%</strong>
            </div>
          </div>

          <div className={riskClass(crowd.risk)}>
            Risk: <b>{crowd.risk || "normal"}</b> | Behavior: <b>{behavior.dominant || "none"}</b> | Agitation:{" "}
            <b>{(behavior.agitation_score || 0).toFixed(2)}</b>
          </div>

          <div className="crowd-meta">
            <span>Detection persons: {people.from_detection ?? 0}</span>
            <span>Pose persons: {people.from_pose ?? 0}</span>
            <span>Pose enabled: {payload.pose_enabled ? "yes" : "no"}</span>
          </div>

          <div className="crowd-behaviors">
            {Object.entries(behavior.counts || {}).map(([label, count]) => (
              <div key={label} className="crowd-chip">
                <span>{label.replace("_", " ")}</span>
                <b>{count}</b>
              </div>
            ))}
          </div>

          <ul className="list">
            {objectSummary.length === 0 ? (
              <li>
                <span className="label">Objects</span>
                <span className="bbox">No objects reported yet</span>
              </li>
            ) : (
              objectSummary.map(([label, count]) => (
                <li key={label}>
                  <span className="label">{label}</span>
                  <span className="confidence">{count}</span>
                </li>
              ))
            )}
          </ul>
        </>
      )}

      {error && <div className="error">{error}</div>}
    </div>
  );
}
