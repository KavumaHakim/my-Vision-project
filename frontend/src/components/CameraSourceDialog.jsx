import { useEffect, useState } from "react";
import { getCameraSource, setCameraSource } from "../api.js";

const STORAGE_KEY = "visionv1.cameraSource";

export default function CameraSourceDialog({ open, onClose }) {
  const [value, setValue] = useState("");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    const local = localStorage.getItem(STORAGE_KEY);
    if (local) {
      setValue(local);
      return;
    }
    getCameraSource()
      .then((data) => {
        if (data?.source !== undefined && data?.source !== null) {
          setValue(String(data.source));
        }
      })
      .catch(() => {});
  }, [open]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus("saving");
    setError(null);
    try {
      const response = await setCameraSource(value);
      localStorage.setItem(STORAGE_KEY, String(response.source ?? value));
      setStatus("saved");
      onClose?.();
    } catch (err) {
      setError(err.message || "Failed to set camera source.");
      setStatus("idle");
    }
  };

  if (!open) return null;

  return (
    <div className="modal-shell">
      <div className="modal-card">
        <div>
          <h2>Connect Camera Endpoint</h2>
          <p className="muted">
            Enter a Raspberry Pi stream URL (e.g. `http://pi.local:8080/video` or `rtsp://pi.local:8554/stream`).
            Use `0` for the local webcam.
          </p>
        </div>
        <form className="modal-form" onSubmit={handleSubmit}>
          <input
            className="input"
            placeholder="http://pi.local:8080/video"
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
          <div className="modal-actions">
            <button type="button" className="ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={status === "saving"}>
              {status === "saving" ? "Connecting..." : "Connect"}
            </button>
          </div>
        </form>
        {error && <div className="error">{error}</div>}
      </div>
    </div>
  );
}
