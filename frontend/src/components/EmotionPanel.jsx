import { useState } from "react";
import { emotionLive, emotionUpload } from "../api.js";

export default function EmotionPanel() {
  const [status, setStatus] = useState("idle");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const handleLive = async () => {
    setStatus("analyzing");
    setResult(null);
    try {
      const res = await emotionLive();
      setResult(res.result || null);
      setStatus("done");
    } catch (err) {
      setStatus(err.message || "failed");
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setStatus("image_required");
      return;
    }
    setStatus("analyzing");
    setResult(null);
    try {
      const res = await emotionUpload(file);
      setResult(res.result || null);
      setStatus("done");
    } catch (err) {
      setStatus(err.message || "failed");
    }
  };

  return (
    <div className="emotion-panel">
      <div className="emotion-actions">
        <button className="face-action-button" onClick={handleLive}>
          Analyze Live
        </button>
        <div className="file">
          <input
            className="file-input"
            type="file"
            accept="image/*"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button className="face-action-button" onClick={handleUpload}>
            Analyze Upload
          </button>
        </div>
      </div>
      <div className="muted">Status: {status}</div>
      {Array.isArray(result) && (
        <ul className="list">
          {result.slice(0, 5).map((item) => (
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
