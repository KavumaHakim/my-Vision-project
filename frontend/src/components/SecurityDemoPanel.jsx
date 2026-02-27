import { useEffect, useState } from "react";
import { getSecurityLast, securityUnknownFrameUrl } from "../api.js";

export default function SecurityDemoPanel() {
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      setStatus("loading");
      try {
        const res = await getSecurityLast();
        if (mounted) {
          setResult(res.result || null);
          setStatus("ready");
        }
      } catch (err) {
        if (mounted) setStatus(err.message || "failed");
      }
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const unknowns = result?.unknowns || [];
  const preview = unknowns[0];

  return (
    <div className="security-demo">
      <div className="muted">Status: {status}</div>
      <div className="security-summary">
        Unknowns detected: <strong>{unknowns.length}</strong>
      </div>
      <div className="muted">
        Alert after {result?.threshold_s ?? 5}s of continuous presence.
      </div>
      {preview && (
        <div className="security-preview">
          <img
            src={`${securityUnknownFrameUrl(preview.id)}&t=${Date.now()}`}
            alt={`Unknown ${preview.id}`}
          />
          <div className="muted">Unknown #{preview.id}</div>
        </div>
      )}
      {unknowns.length === 0 ? (
        <div className="muted">No unknown faces currently detected.</div>
      ) : (
        <ul className="list">
          {unknowns.map((item) => (
            <li key={item.id}>
              <span className="label">Unknown #{item.id}</span>
              <span className="confidence">
                {item.alerted ? "ALERT" : `${item.duration_s}s`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
