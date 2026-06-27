import { useEffect, useMemo, useRef, useState } from "react";
import {
  streamUrl,
  setViewMode,
  recordingStart,
  recordingStop,
  recordingStatus,
} from "../api.js";

export default function VideoStream() {
  const [nonce, setNonce] = useState(0);
  const [status, setStatus] = useState("connecting");
  const [view, setView] = useState("inference"); // "inference" | "smooth"
  const [overlay, setOverlay] = useState(true);   // draw boxes on the smooth feed
  const [recording, setRecording] = useState(false);
  const [recInfo, setRecInfo] = useState(null);
  const [busy, setBusy] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef(null);

  // Single persistent stream — the view is switched server-side, so the src
  // (and thus the MJPEG connection) never changes when toggling views.
  const src = useMemo(() => `${streamUrl()}?t=${nonce}`, [nonce]);

  // Push the desired mode to the backend on mount and whenever it changes.
  useEffect(() => {
    const mode =
      view === "inference" ? "inference" : overlay ? "smooth" : "smooth_raw";
    setViewMode(mode).catch(() => {});
  }, [view, overlay]);

  useEffect(() => {
    const refresh = setInterval(() => setNonce((n) => n + 1), 60000);
    return () => clearInterval(refresh);
  }, []);

  useEffect(() => {
    setStatus("connecting");
    const timer = setTimeout(() => {
      setStatus((s) => (s === "connecting" ? "live" : s));
    }, 3000);
    return () => clearTimeout(timer);
  }, [src]);

  // Keep the recording indicator in sync with the backend.
  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const s = await recordingStatus();
        if (mounted) {
          setRecording(!!s.recording);
          setRecInfo(s);
        }
      } catch {
        /* ignore transient errors */
      }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  // Track fullscreen state (covers Esc and the button alike).
  useEffect(() => {
    const onChange = () => setIsFullscreen(document.fullscreenElement === containerRef.current);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleFullscreen = () => {
    const el = containerRef.current;
    if (!el) return;
    if (document.fullscreenElement) {
      document.exitFullscreen?.();
    } else {
      el.requestFullscreen?.();
    }
  };

  const switchView = (next) => {
    if (next === view) return;
    setView(next); // mode is pushed server-side; the stream stays connected
  };

  const toggleRecord = async () => {
    setBusy(true);
    try {
      if (recording) {
        await recordingStop();
      } else {
        await recordingStart();
      }
      const s = await recordingStatus();
      setRecording(!!s.recording);
      setRecInfo(s);
    } catch {
      /* leave state as-is; next poll will reconcile */
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="video" ref={containerRef}>
      <div className="video-toolbar">
        <div className="view-toggle">
          <button
            className={view === "inference" ? "vt-btn active" : "vt-btn"}
            onClick={() => switchView("inference")}
          >
            Inference
          </button>
          <button
            className={view === "smooth" ? "vt-btn active" : "vt-btn"}
            onClick={() => switchView("smooth")}
          >
            Smooth
          </button>
        </div>
        {view === "smooth" && (
          <button
            className={overlay ? "vt-btn active" : "vt-btn"}
            onClick={() => setOverlay((o) => !o)}
            title="Overlay the latest detection boxes on the smooth feed"
          >
            Boxes
          </button>
        )}
        <button
          className={recording ? "rec-btn recording" : "rec-btn"}
          onClick={toggleRecord}
          disabled={busy}
        >
          {recording ? "■ Stop" : "● Record"}
        </button>
        <button
          className="vt-btn fs-btn"
          onClick={toggleFullscreen}
          title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
        >
          {isFullscreen ? "⤡ Exit" : "⤢ Full"}
        </button>
      </div>

      <img
        src={src}
        alt="Live stream"
        onLoad={() => setStatus("live")}
        onError={() => {
          setStatus("reconnecting");
          setTimeout(() => setNonce((n) => n + 1), 2000);
        }}
      />

      {recording && (
        <div className="rec-indicator">
          ● REC{recInfo?.duration_s ? ` ${recInfo.duration_s}s` : ""}
        </div>
      )}

      <div className={`video-status${status === "reconnecting" ? " reconnecting" : ""}`}>
        {status}
        {view === "smooth" ? " · smooth" : ""}
      </div>
    </div>
  );
}
