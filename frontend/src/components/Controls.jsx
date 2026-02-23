import { useState } from "react";
import { captureImage } from "../api.js";

export default function Controls() {
  const [status, setStatus] = useState("idle");
  const [lastUrl, setLastUrl] = useState(null);

  const handleCapture = async () => {
    setStatus("capturing");
    try {
      const res = await captureImage();
      setLastUrl(res.upload_url || null);
      setStatus(res.ok ? "uploaded" : "failed");
    } catch (err) {
      setStatus(err.message || "failed");
    }
  };

  return (
    <div className="controls">
      <button onClick={handleCapture}>Capture Image Now</button>
      <div className="muted">Status: {status}</div>
      {lastUrl && (
        <div className="muted">
          Last upload: <a href={lastUrl} target="_blank" rel="noreferrer">open</a>
        </div>
      )}
    </div>
  );
}
