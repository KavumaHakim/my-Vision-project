import { useEffect, useMemo, useState } from "react";
import { streamUrl } from "../api.js";

export default function VideoStream() {
  const [nonce, setNonce] = useState(0);
  const [status, setStatus] = useState("connecting");

  const src = useMemo(() => `${streamUrl()}?t=${nonce}`, [nonce]);

  useEffect(() => {
    const id = setInterval(() => {
      setNonce((n) => n + 1);
    }, 60000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="video">
      <img
        src={src}
        alt="Live stream"
        onLoad={() => setStatus("live")}
        onError={() => {
          setStatus("reconnecting");
          setTimeout(() => setNonce((n) => n + 1), 1000);
        }}
      />
      <div className="video-status">{status}</div>
    </div>
  );
}
