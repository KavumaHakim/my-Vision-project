import { useEffect, useState } from "react";
import VideoStream from "./VideoStream.jsx";
import { faceRecognizeLive, faceRegisterLive, listFaces } from "../api.js";

const SCORE_THRESHOLD = 0.45;

export default function LoginPage({ onLogin }) {
  // mode: "checking" | "register" | "recognize" | "bypass"
  const [mode, setMode]         = useState("checking");
  const [auto, setAuto]         = useState(false);
  const [scanStatus, setScan]   = useState("idle");
  const [scanError, setScanErr] = useState(null);
  const [regName, setRegName]   = useState("");
  const [regStatus, setRegSt]   = useState("idle"); // "idle"|"registering"|"done"
  const [regError, setRegErr]   = useState(null);
  const [manualName, setManual] = useState("");

  // On mount: decide whether to go straight to registration or recognition
  useEffect(() => {
    listFaces()
      .then((data) => {
        if (data.faces && data.faces.length === 0) {
          setMode("register");
        } else {
          setMode("recognize");
          setAuto(true);
        }
      })
      .catch(() => {
        setMode("recognize");
        setAuto(true);
      });
  }, []);

  // Auto-scan interval (only in recognize mode)
  const attemptLogin = async () => {
    setScan("scanning");
    setScanErr(null);
    try {
      const res  = await faceRecognizeLive();
      const best = res.best;
      if (best && best.score >= SCORE_THRESHOLD) {
        setScan("success");
        onLogin({ name: best.name, score: best.score });
        return;
      }
      setScan("no_match");
    } catch (err) {
      const msg = err.message || "failed";
      if (msg === "face_service_disabled" || msg === "camera_unavailable") {
        setMode("bypass");
        setAuto(false);
      }
      setScan("failed");
      setScanErr(msg);
    }
  };

  useEffect(() => {
    if (!auto || mode !== "recognize") return;
    const id = setInterval(attemptLogin, 4000);
    return () => clearInterval(id);
  }, [auto, mode]);

  // First-time face registration
  const handleRegister = async () => {
    const name = regName.trim();
    if (!name) return;
    setRegSt("registering");
    setRegErr(null);
    try {
      await faceRegisterLive(name);
      setRegSt("done");
      setTimeout(() => onLogin({ name, score: 1 }), 700);
    } catch (err) {
      const msg = err.message || "register_failed";
      setRegErr(
        msg === "no_face"
          ? "No face detected — look directly at the camera and try again."
          : msg === "camera_unavailable"
          ? "Camera not ready yet — wait a moment and try again."
          : `Registration failed: ${msg}`
      );
      setRegSt("idle");
    }
  };

  const handleManualLogin = () => {
    const name = manualName.trim();
    if (!name) return;
    onLogin({ name, score: 1 });
  };

  const streamLabel =
    mode === "register"  ? "Look at the camera to register"
    : mode === "bypass"  ? "Face ID offline"
    : "Face ID ready";

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-brand">
          <span className="chip">Vision V1</span>
          <h1>
            {mode === "register" ? "First-time setup" : "Secure access with Face ID"}
          </h1>
          <p>
            {mode === "register"
              ? "No faces are registered yet. Enter your name and register your face to get started."
              : mode === "checking"
              ? "Checking database…"
              : "Step into view and we will authenticate using live recognition."}
          </p>
        </div>

        {mode === "checking" && (
          <div className="login-actions">
            <div className="muted">Loading…</div>
          </div>
        )}

        {mode === "register" && (
          <div className="login-actions">
            <input
              className="input"
              value={regName}
              onChange={(e) => setRegName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRegister()}
              placeholder="Your name"
              autoFocus
              disabled={regStatus === "registering" || regStatus === "done"}
            />
            <button
              className="primary"
              onClick={handleRegister}
              disabled={!regName.trim() || regStatus === "registering" || regStatus === "done"}
            >
              {regStatus === "registering"
                ? "Registering…"
                : regStatus === "done"
                ? "Registered! Logging in…"
                : "Register My Face"}
            </button>
            {regError && <div className="login-bypass-notice">{regError}</div>}
          </div>
        )}

        {mode === "recognize" && (
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
              Status: {scanStatus}
              {scanError ? ` · ${scanError}` : ""}
            </div>
          </div>
        )}

        {mode === "bypass" && (
          <div className="login-actions">
            <div className="login-bypass-notice">
              {scanError === "camera_unavailable"
                ? "Camera not ready — enter your name to continue."
                : "Face service offline — enter your name to continue."}
            </div>
            <input
              className="input"
              value={manualName}
              onChange={(e) => setManual(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleManualLogin()}
              placeholder="Your name"
              autoFocus
            />
            <button className="primary" onClick={handleManualLogin} disabled={!manualName.trim()}>
              Continue
            </button>
            <button
              className="login-retry"
              onClick={() => { setMode("recognize"); setAuto(true); setScanErr(null); }}
            >
              Retry Face ID
            </button>
          </div>
        )}
      </div>

      <div className="login-stream">
        <div className="login-stream-head">
          <span>Live Camera</span>
          <span className="muted">{streamLabel}</span>
        </div>
        <VideoStream />
      </div>
    </div>
  );
}
