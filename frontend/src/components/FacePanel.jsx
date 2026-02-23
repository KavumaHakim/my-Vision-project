import { useEffect, useState } from "react";
import {
  faceLast,
  faceRegisterLive,
  faceRegisterUpload,
  faceRecognizeLive,
  faceRecognizeUpload
} from "../api.js";

export default function FacePanel() {
  const [name, setName] = useState("");
  const [regStatus, setRegStatus] = useState("idle");
  const [recStatus, setRecStatus] = useState("idle");
  const [regFile, setRegFile] = useState(null);
  const [recFile, setRecFile] = useState(null);
  const [best, setBest] = useState(null);
  const [enabled, setEnabled] = useState(false);
  const [tab, setTab] = useState("register");
  const [lastAuto, setLastAuto] = useState(null);

  useEffect(() => {
    if (!enabled) {
      setLastAuto(null);
      return;
    }
    let mounted = true;
    const poll = async () => {
      try {
        const res = await faceLast();
        if (mounted) setLastAuto(res.result || null);
      } catch {
        if (mounted) setLastAuto(null);
      }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [enabled]);

  const handleRegisterLive = async () => {
    if (!enabled) return;
    if (!name.trim()) {
      setRegStatus("name_required");
      return;
    }
    setRegStatus("registering");
    try {
      await faceRegisterLive(name.trim());
      setRegStatus("registered");
    } catch (err) {
      setRegStatus(err.message || "failed");
    }
  };

  const handleRegisterUpload = async () => {
    if (!enabled) return;
    if (!name.trim()) {
      setRegStatus("name_required");
      return;
    }
    if (!regFile) {
      setRegStatus("image_required");
      return;
    }
    setRegStatus("registering");
    try {
      await faceRegisterUpload(name.trim(), regFile);
      setRegStatus("registered");
    } catch (err) {
      setRegStatus(err.message || "failed");
    }
  };

  const handleRecognizeLive = async () => {
    if (!enabled) return;
    setRecStatus("recognizing");
    setBest(null);
    try {
      const res = await faceRecognizeLive();
      setBest(res.best || null);
      setRecStatus(res.best ? "matched" : "unknown");
    } catch (err) {
      setRecStatus(err.message || "failed");
    }
  };

  const handleRecognizeUpload = async () => {
    if (!enabled) return;
    if (!recFile) {
      setRecStatus("image_required");
      return;
    }
    setRecStatus("recognizing");
    setBest(null);
    try {
      const res = await faceRecognizeUpload(recFile);
      setBest(res.best || null);
      setRecStatus(res.best ? "matched" : "unknown");
    } catch (err) {
      setRecStatus(err.message || "failed");
    }
  };

  return (
    <div className="face-panel">
      <div className="face-toggle">
        <label className="toggle">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(event) => setEnabled(event.target.checked)}
          />
          Enable Facial Recognition
        </label>
        <div className="muted">Status: {enabled ? "enabled" : "disabled"}</div>
        {enabled && (
          <div className="muted">
            Auto recognition:{" "}
            {lastAuto?.best ? (
              <>
                <strong>{lastAuto.best.name}</strong>{" "}
                ({lastAuto.best.score.toFixed(3)})
              </>
            ) : (
              "unknown"
            )}
          </div>
        )}
      </div>

      <div className="tabs">
        <button
          className={tab === "register" ? "tab-button active" : "tab-button"}
          onClick={() => setTab("register")}
          disabled={!enabled}
        >
          Registration
        </button>
        <button
          className={tab === "recognize" ? "tab-button active" : "tab-button"}
          onClick={() => setTab("recognize")}
          disabled={!enabled}
        >
          Recognition
        </button>
      </div>

      {tab === "register" ? (
        <div className="face-block">
          <div className="face-row">
            <label className="label">Name</label>
            <input
              className="input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Shami"
              disabled={!enabled}
            />
          </div>
          <div className="face-actions">
            <button className="face-action-button" onClick={handleRegisterLive} disabled={!enabled}>
              Register From Live
            </button>
            <div className="file">
              <input
                className="file-input"
                type="file"
                accept="image/*"
                onChange={(event) => setRegFile(event.target.files?.[0] || null)}
                disabled={!enabled}
              />
              <button className="face-action-button" onClick={handleRegisterUpload} disabled={!enabled}>
                Register From Upload
              </button>
            </div>
          </div>
          <div className="muted">Register status: {regStatus}</div>
        </div>
      ) : (
        <div className="face-block">
          <div className="face-actions">
            <button className="face-action-button" onClick={handleRecognizeLive} disabled={!enabled}>
              Recognize From Live
            </button>
            <div className="file">
              <input
                className="file-input"
                type="file"
                accept="image/*"
                onChange={(event) => setRecFile(event.target.files?.[0] || null)}
                disabled={!enabled}
              />
              <button className="face-action-button" onClick={handleRecognizeUpload} disabled={!enabled}>
                Recognize From Upload
              </button>
            </div>
          </div>
          <div className="muted">Recognition status: {recStatus}</div>
          {best && (
            <div className="match">
              Best match: <strong>{best.name}</strong> ({best.score.toFixed(3)})
            </div>
          )}
        </div>
      )}
    </div>
  );
}
