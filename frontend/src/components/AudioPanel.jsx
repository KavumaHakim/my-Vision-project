import { useEffect, useState } from "react";
import { getAudioLast } from "../api.js";

export default function AudioPanel() {
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      setStatus("loading");
      try {
        const res = await getAudioLast();
        if (mounted) {
          setResult(res.result || null);
          setStatus("ready");
        }
      } catch (err) {
        if (mounted) setStatus(err.message || "failed");
      }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const alert = result?.alert;

  return (
    <div className="audio-panel">
      <div className="muted">Status: {status}</div>
      {alert ? (
        <div className="audio-alert">
          {alert.label} <span>({alert.score.toFixed(3)})</span>
        </div>
      ) : (
        <div className="muted">No alert detected.</div>
      )}
      {Array.isArray(result?.results) && (
        <ul className="list">
          {result.results.slice(0, 5).map((item) => (
            <li key={item.label}>
              <span className="label">{item.label}</span>
              <span className="confidence">{item.score.toFixed(3)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
