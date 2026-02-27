import { useEffect, useState } from "react";
import VideoStream from "./components/VideoStream.jsx";
import DetectionPanel from "./components/DetectionPanel.jsx";
import Controls from "./components/Controls.jsx";
import FacePanel from "./components/FacePanel.jsx";
import EmotionPanel from "./components/EmotionPanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";
import ActionPanel from "./components/ActionPanel.jsx";
import AudioPanel from "./components/AudioPanel.jsx";
import LoginPage from "./components/LoginPage.jsx";
import DemosPage from "./components/DemosPage.jsx";
import { getHealth } from "./api.js";

export default function App() {
  const [health, setHealth] = useState({
    ok: false,
    camera: false,
    model: false,
    uploader: false
  });
  const [session, setSession] = useState(null);
  const [view, setView] = useState("login");

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

  const handleLogin = (user) => {
    setSession(user);
    setView("dashboard");
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="dot" />
          <div>
            <div className="brand-title">Vision V1</div>
            <div className="brand-sub">Real‑time vision intelligence</div>
          </div>
        </div>
        <nav className="nav">
          <button
            className={view === "dashboard" ? "nav-link active" : "nav-link"}
            onClick={() => setView("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={view === "demos" ? "nav-link active" : "nav-link"}
            onClick={() => setView("demos")}
          >
            Demos
          </button>
        </nav>
        <div className="session">
          {session ? (
            <>
              <div className="session-user">
                {session.name} <span>{session.score.toFixed(2)}</span>
              </div>
              <button
                className="ghost"
                onClick={() => {
                  setSession(null);
                  setView("login");
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <button className="ghost" onClick={() => setView("login")}>
              Sign in
            </button>
          )}
        </div>
      </header>

      {view === "login" && <LoginPage onLogin={handleLogin} />}
      {view === "demos" && <DemosPage />}
      {view === "dashboard" && (
        <>
          <section className="status-row">
            <div className="status-card">
              <div className="label">Backend</div>
              <div className={health.ok ? "pill ok" : "pill"}>Online</div>
            </div>
            <div className="status-card">
              <div className="label">Camera</div>
              <div className={health.camera ? "pill ok" : "pill"}>Ready</div>
            </div>
            <div className="status-card">
              <div className="label">Model</div>
              <div className={health.model ? "pill ok" : "pill"}>Loaded</div>
            </div>
            <div className="status-card">
              <div className="label">Uploader</div>
              <div className={health.uploader ? "pill ok" : "pill"}>Active</div>
            </div>
          </section>

          <main className="grid">
            <section className="card video-card">
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
            <section className="card">
              <h2>Emotion Detection</h2>
              <EmotionPanel />
            </section>
            <section className="card">
              <h2>Audio Alerts</h2>
              <AudioPanel />
            </section>
            <section className="card">
              <h2>Action Tracking</h2>
              <ActionPanel />
            </section>
            <section className="card">
              <h2>Behavior Timeline</h2>
              <TimelinePanel />
            </section>
            <section className="card">
              <h2>Face Registration & Recognition</h2>
              <FacePanel />
            </section>
          </main>
        </>
      )}
    </div>
  );
}
