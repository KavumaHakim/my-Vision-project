import { useEffect, useMemo, useState } from "react";
import { streamUrl } from "../api.js";

export default function VideoStream() {
  const [nonce, setNonce] = useState(0);
  const [status, setStatus] = useState("connecting");

  const src = useMemo(() => `${streamUrl()}?t=${nonce}`, [nonce]);

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

  return (
    <div className="video">
      <img
        src={src}
        alt="Live stream"
        onLoad={() => setStatus("live")}
        onError={() => {
          setStatus("reconnecting");
          setTimeout(() => setNonce((n) => n + 1), 2000);
        }}
      />
      <div className={`video-status${status === "reconnecting" ? " reconnecting" : ""}`}>{status}</div>
    </div>
  );
}
