import { useEffect, useMemo, useState } from "react";
import VideoStream from "./components/VideoStream.jsx";
import DetectionPanel from "./components/DetectionPanel.jsx";
import Controls from "./components/Controls.jsx";
import FacePanel from "./components/FacePanel.jsx";
import EmotionPanel from "./components/EmotionPanel.jsx";
import TimelinePanel from "./components/TimelinePanel.jsx";
import ModelDashboard from "./components/ModelDashboard.jsx";
import CrowdPanel from "./components/CrowdPanel.jsx";
import CameraSourceDialog from "./components/CameraSourceDialog.jsx";
import LoginPage from "./components/LoginPage.jsx";
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
    blurb: "Face recognition and registration."
  },
  {
    id: "intelligence",
    label: "Intelligence",
    blurb: "Emotion model outputs."
  },
  {
    id: "analytics",
    label: "Crowd Analytics",
    blurb: "Fused object and pose behavior analysis."
  },
  {
    id: "timeline",
    label: "Timeline",
    blurb: "Behavior history."
  }
];

function HealthPills({ health }) {
  return (
    <div className="workspace-pills">
      <div className={health.ok ? "pill ok" : "pill"}>{health.ok ? "Backend" : "Backend Down"}</div>
      <div className={health.camera ? "pill ok" : "pill"}>{health.camera ? "Camera Ready" : "No Camera"}</div>
      <div className={health.model ? "pill ok" : "pill"}>{health.model ? "Model Loaded" : "Model Offline"}</div>
      <div className={health.motion ? "pill ok" : "pill"}>{health.motion ? "Motion Active" : "Motion Idle"}</div>
    </div>
  );
}

function OverviewPage({ health }) {
  return (
    <div className="page-grid">
      <section className="card model-dashboard-card">
        <ModelDashboard health={health} />
      </section>
      <section className="card live-stream-card">
        <h2>Live Stream</h2>
        <VideoStream />
      </section>
      <section className="card">
        <h2>Controls</h2>
        <Controls />
      </section>
      <section className="card">
        <h2>Crowd Snapshot</h2>
        <CrowdPanel />
      </section>
    </div>
  );
}

function VisionOpsPage() {
  return (
    <div className="page-grid">
      <section className="card live-stream-card">
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
    </div>
  );
}

function IntelligencePage() {
  return (
    <div className="page-grid">
      <section className="card">
        <h2>Emotion Detection</h2>
        <EmotionPanel />
      </section>
    </div>
  );
}

function CrowdAnalyticsPage() {
  return (
    <div className="page-grid">
      <section className="card">
        <h2>Behavior and Crowd Analysis</h2>
        <CrowdPanel />
      </section>
      <section className="card">
        <h2>Live Detection Feed</h2>
        <DetectionPanel />
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
  const [showCameraDialog, setShowCameraDialog] = useState(false);

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
    setShowCameraDialog(true);
  };

  let content = null;
  if (page === "overview") content = <OverviewPage health={health} />;
  if (page === "vision") content = <VisionOpsPage />;
  if (page === "identity") content = <IdentityPage />;
  if (page === "intelligence") content = <IntelligencePage />;
  if (page === "analytics") content = <CrowdAnalyticsPage />;
  if (page === "timeline") content = <TimelinePage />;

  if (!session) {
    return (
      <div className="app">
        <LoginPage onLogin={handleLogin} />
      </div>
    );
  }

  return (
    <div className="workspace-shell">
      <CameraSourceDialog open={showCameraDialog} onClose={() => setShowCameraDialog(false)} />
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
          <button className="ghost" onClick={() => setShowCameraDialog(true)}>
            Camera Source
          </button>
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
