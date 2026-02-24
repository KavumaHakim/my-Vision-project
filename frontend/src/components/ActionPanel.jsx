import { useEffect, useState } from "react";
import { getActionLast } from "../api.js";

export default function ActionPanel() {
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      setStatus("loading");
      try {
        const res = await getActionLast();
        if (mounted) {
          setResult(res.result || null);
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
    <div className="action-panel">
      <div className="muted">Status: {status}</div>
      {result?.best && (
        <div className="action-best">
          {result.best.label} <span>({result.best.score.toFixed(3)})</span>
        </div>
      )}
      {Array.isArray(result?.topk) && result.topk.length > 0 && (
        <ul className="list">
          {result.topk.map((item) => (
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
