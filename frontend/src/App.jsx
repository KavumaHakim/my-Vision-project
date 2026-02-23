import { useEffect, useState } from "react";
import VideoStream from "./components/VideoStream.jsx";
import DetectionPanel from "./components/DetectionPanel.jsx";
import Controls from "./components/Controls.jsx";
import { getHealth } from "./api.js";

export default function App() {
  const [health, setHealth] = useState({
    ok: false,
    camera: false,
    model: false,
    uploader: false
  });

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const data = await getHealth();
        if (mounted) setHealth(data);
      } catch {
        if (mounted) {
          setHealth({ ok: false, camera: false, model: false, uploader: false });
        }
      }
    };
    poll();
    const id = setInterval(poll, 3000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Vision V1</h1>
          <p>Local AI vision with FastAPI + React</p>
        </div>
        <div className="status">
          <span className={health.ok ? "badge ok" : "badge"}>Backend</span>
          <span className={health.camera ? "badge ok" : "badge"}>Camera</span>
          <span className={health.model ? "badge ok" : "badge"}>Model</span>
          <span className={health.uploader ? "badge ok" : "badge"}>Uploader</span>
        </div>
      </header>

      <main className="grid">
        <section className="card">
          <h2>Live Stream</h2>
          <VideoStream />
        </section>
        <section className="card">
          <h2>Detections</h2>
          <DetectionPanel />
        </section>
        <section className="card">
          <h2>Controls</h2>
          <Controls />
        </section>
      </main>
    </div>
  );
}
