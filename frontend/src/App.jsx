import { useEffect, useMemo, useState } from "react";
import VideoStream from "./components/VideoStream.jsx";
import DetectionPanel from "./components/DetectionPanel.jsx";
import Controls from "./components/Controls.jsx";
import FacePanel from "./components/FacePanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";
import ActionPanel from "./components/ActionPanel.jsx";
import AudioPanel from "./components/AudioPanel.jsx";
import ModelDashboard from "./components/ModelDashboard.jsx";
import LoginPage from "./components/LoginPage.jsx";
import DemosPage from "./components/DemosPage.jsx";
import SecurityDemoPanel from "./components/SecurityDemoPanel.jsx";
import AttendanceDemoPanel from "./components/AttendanceDemoPanel.jsx";
import { getHealth } from "./api.js";

const PAGES = [
  {
    id: "overview",
    label: "Overview",
    blurb: "Model orchestration and platform health."
  },
  {
    id: "vision",
    label: "Vision Ops",
    blurb: "Live stream, detection feed, and capture controls."
  },
  {
    id: "identity",
    label: "Identity",
    blurb: "Face recognition, security alerts, and attendance."
  },
  {
    id: "intelligence",
    label: "Intelligence",
    blurb: "Action and audio model outputs."
  },
  {
    id: "timeline",
    label: "Timeline",
    blurb: "Behavior and attendance history."
  },
  {
    id: "demos",
    label: "Demos",
    blurb: "Scenario-driven live demonstrations."
  }
];

function HealthPills({ health }) {
  const ok = health.ok && health.camera_live && health.model;
  const label = !health.ok ? "Backend offline"
    : !health.camera ? "No camera"
    : !health.camera_live ? "Camera: no frames"
    : !health.model ? "Model offline"
    : "System online";
  return <div className={ok ? "pill ok" : "pill"}>{label}</div>;
}

function OverviewPage({ health }) {
  return (
    <div className="page-grid">
      <section className="card model-dashboard-card">
        <ModelDashboard health={health} />
      </section>
      <section className="card">
        <h2>Live Stream</h2>
        <VideoStream />
      </section>
      <section className="card">
        <h2>Controls</h2>
        <Controls />
      </section>
      <section className="card">
        <h2>Action Snapshot</h2>
        <ActionPanel />
      </section>
      <section className="card">
        <h2>Audio Snapshot</h2>
        <AudioPanel />
      </section>
    </div>
  );
}

function VisionOpsPage() {
  return (
    <div className="vision-ops-grid">
      <section className="card vision-stream-card">
        <h2>Live Stream</h2>
        <VideoStream />
      </section>
      <section className="card">
        <h2>Detection Feed</h2>
        <DetectionPanel />
      </section>
      <section className="card">
        <h2>Capture Controls</h2>
        <Controls />
      </section>
    </div>
  );
}

function IdentityPage() {
  return (
    <div className="page-grid">
      <section className="card">
        <h2>Face Registration & Recognition</h2>
        <FacePanel />
      </section>
      <section className="card">
        <h2>Security Monitor</h2>
        <SecurityDemoPanel />
      </section>
      <section className="card">
        <h2>Attendance</h2>
        <AttendanceDemoPanel />
      </section>
    </div>
  );
}

function IntelligencePage() {
  return (
    <div className="page-grid">
      <section className="card">
        <h2>Action Tracking</h2>
        <ActionPanel />
      </section>
      <section className="card">
        <h2>Audio Alerts</h2>
        <AudioPanel />
      </section>
    </div>
  );
}

function TimelinePage() {
  return (
    <div className="page-grid">
      <section className="card">
        <h2>Behavior Timeline</h2>
        <TimelinePanel />
      </section>
      <section className="card">
        <h2>Attendance Summary</h2>
        <AttendanceDemoPanel />
      </section>
    </div>
  );
}

export default function App() {
  const [health, setHealth] = useState({
    ok: false,
    camera: false,
    model: false,
    uploader: false
  });
  const [session, setSession] = useState(null);
  const [page, setPage] = useState("overview");

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

  const pageInfo = useMemo(
    () => PAGES.find((item) => item.id === page) || PAGES[0],
    [page]
  );

  const handleLogin = (user) => {
    setSession(user);
    setPage("overview");
  };

  let content = null;
  if (page === "overview") content = <OverviewPage health={health} />;
  if (page === "vision") content = <VisionOpsPage />;
  if (page === "identity") content = <IdentityPage />;
  if (page === "intelligence") content = <IntelligencePage />;
  if (page === "timeline") content = <TimelinePage />;
  if (page === "demos") content = <DemosPage />;

  if (!session) {
    return (
      <div className="app">
        <LoginPage onLogin={handleLogin} />
      </div>
    );
  }

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="sidebar-brand">
          <span className="dot" />
          <div>
            <div className="brand-title">Vision V1</div>
            <div className="brand-sub">Model Dashboard</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {PAGES.map((item) => (
            <button
              key={item.id}
              className={page === item.id ? "sidebar-link active" : "sidebar-link"}
              onClick={() => setPage(item.id)}
            >
              <span>{item.label}</span>
              <small>{item.blurb}</small>
            </button>
          ))}
        </nav>

        <div className="sidebar-session">
          <div className="session-user">
            {session.name} <span>{session.score.toFixed(2)}</span>
          </div>
          <button
            className="ghost"
            onClick={() => {
              setSession(null);
              setPage("overview");
            }}
          >
            Log out
          </button>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div>
            <h1>{pageInfo.label}</h1>
            <p>{pageInfo.blurb}</p>
          </div>
          <HealthPills health={health} />
        </header>
        <section className="workspace-content">{content}</section>
      </main>
    </div>
  );
}
