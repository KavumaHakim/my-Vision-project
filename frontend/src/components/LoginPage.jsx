import { useEffect, useState } from "react";
import VideoStream from "./VideoStream.jsx";
import { faceRecognizeLive } from "../api.js";

const SCORE_THRESHOLD = 0.45;

export default function LoginPage({ onLogin }) {
  const [status, setStatus] = useState("idle");
  const [auto, setAuto] = useState(true);
  const [error, setError] = useState(null);
  const [faceDisabled, setFaceDisabled] = useState(false);
  const [manualName, setManualName] = useState("");

  const attemptLogin = async () => {
    setStatus("scanning");
    setError(null);
    try {
      const res = await faceRecognizeLive();
      const best = res.best;
      if (best && best.score >= SCORE_THRESHOLD) {
        onLogin({ name: best.name, score: best.score });
        setStatus("success");
        return;
      }
      setStatus("no_match");
    } catch (err) {
      const msg = err.message || "failed";
      if (msg === "face_service_disabled" || msg === "camera_unavailable") {
        setFaceDisabled(true);
        setAuto(false);
      }
      setStatus("failed");
      setError(msg);
    }
  };

  useEffect(() => {
    if (!auto) return;
    const id = setInterval(attemptLogin, 4000);
    return () => clearInterval(id);
  }, [auto]);

  const handleManualLogin = () => {
    const name = manualName.trim();
    if (!name) return;
    onLogin({ name, score: 1 });
  };

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-brand">
          <span className="chip">Vision V1</span>
          <h1>Secure access with Face ID</h1>
          <p>
            Step into view and we will authenticate using live recognition.
            You can also toggle auto‑login for continuous scanning.
          </p>
        </div>

        {faceDisabled ? (
          <div className="login-actions">
            <div className="login-bypass-notice">
              {error === "camera_unavailable"
                ? "Camera not ready — enter your name to continue."
                : "Face service offline — enter your name to continue."}
            </div>
            <input
              className="input"
              value={manualName}
              onChange={(e) => setManualName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleManualLogin()}
              placeholder="Your name"
              autoFocus
            />
            <button className="primary" onClick={handleManualLogin} disabled={!manualName.trim()}>
              Continue
            </button>
            <button
              className="login-retry"
              onClick={() => {
                setFaceDisabled(false);
                setAuto(true);
                setError(null);
              }}
            >
              Retry Face ID
            </button>
          </div>
        ) : (
          <div className="login-actions">
            <button className="primary" onClick={attemptLogin}>
              Scan Face ID
            </button>
            <label className="toggle">
              <input
                type="checkbox"
                checked={auto}
                onChange={(e) => setAuto(e.target.checked)}
              />
              Auto‑login every 4s
            </label>
            <div className="muted">
              Status: {status}
              {error ? ` · ${error}` : ""}
            </div>
          </div>
        )}
      </div>

      <div className="login-stream">
        <div className="login-stream-head">
          <span>Live Camera</span>
          <span className="muted">{faceDisabled ? "Face ID offline" : "Face ID ready"}</span>
        </div>
        <VideoStream />
      </div>
    </div>
  );
}
