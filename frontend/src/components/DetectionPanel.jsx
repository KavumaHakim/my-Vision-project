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
      <div className="ts-label">Last update: {data.timestamp || "-"}</div>
      {error && <div className="error">{error}</div>}
      {data.objects.length === 0 ? (
        <div className="muted">No objects detected</div>
      ) : (
        <ul className="detection-list">
          {data.objects.map((obj, idx) => (
            <li className="detection-item" key={`${obj.label}-${idx}`}>
              <span className="detection-label">{obj.label}</span>
              <span className="detection-conf">{Math.round(obj.confidence * 100)}%</span>
              <span className="detection-bbox">{obj.bbox.join(", ")}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
