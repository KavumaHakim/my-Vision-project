import { useEffect, useState } from "react";
import { getDetections } from "../api.js";

export default function DetectionPanel() {
  const [data, setData] = useState({ timestamp: null, objects: [] });
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const res = await getDetections();
        if (mounted) {
          setData(res);
          setError(null);
        }
      } catch (err) {
        if (mounted) setError(err.message);
      }
    };
    poll();
    const id = setInterval(poll, 800);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div>
      <div className="muted">Last update: {data.timestamp || "-"}</div>
      {error && <div className="error">{error}</div>}
      <ul className="list">
        {data.objects.length === 0 && <li>No objects detected</li>}
        {data.objects.map((obj, idx) => (
          <li key={`${obj.label}-${idx}`}>
            <span className="label">{obj.label}</span>
            <span className="confidence">{Math.round(obj.confidence * 100)}%</span>
            <span className="bbox">[{obj.bbox.join(", ")}]</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
