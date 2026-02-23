import { useState } from "react";
import {
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

  const handleRegisterLive = async () => {
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
      <div className="face-block">
        <div className="face-row">
          <label className="label">Name</label>
          <input
            className="input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Shami"
          />
        </div>
        <div className="face-actions">
          <button onClick={handleRegisterLive}>Register From Live</button>
          <div className="file">
            <input
              className="file-input"
              type="file"
              accept="image/*"
              onChange={(event) => setRegFile(event.target.files?.[0] || null)}
            />
            <button onClick={handleRegisterUpload}>Register From Upload</button>
          </div>
        </div>
        <div className="muted">Register status: {regStatus}</div>
      </div>

      <div className="face-block">
        <div className="face-actions">
          <button onClick={handleRecognizeLive}>Recognize From Live</button>
          <div className="file">
            <input
              className="file-input"
              type="file"
              accept="image/*"
              onChange={(event) => setRecFile(event.target.files?.[0] || null)}
            />
            <button onClick={handleRecognizeUpload}>Recognize From Upload</button>
          </div>
        </div>
        <div className="muted">Recognition status: {recStatus}</div>
        {best && (
          <div className="match">
            Best match: <strong>{best.name}</strong> ({best.score.toFixed(3)})
          </div>
        )}
      </div>
    </div>
  );
}
