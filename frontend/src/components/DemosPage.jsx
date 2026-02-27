import SecurityDemoPanel from "./SecurityDemoPanel.jsx";
import AttendanceDemoPanel from "./AttendanceDemoPanel.jsx";

const DEMOS = [
  {
    title: "Security Operations",
    body:
      "Detect unknown faces, track behavior, and raise audio alerts for incidents.",
    tags: ["Face ID", "Action", "Audio Alerts"]
  },
  {
    title: "Attendance & Access",
    body:
      "Automated entry logging with re‑identification and confidence thresholds.",
    tags: ["Attendance", "Re‑ID", "Timeline"]
  },
  {
    title: "Retail Intelligence",
    body:
      "Understand dwell time, customer journeys, and emotional response.",
    tags: ["Emotion", "Behavior", "Insights"]
  },
  {
    title: "Healthcare Monitoring",
    body:
      "Detect agitation, falls, or distress in monitored care spaces.",
    tags: ["Action", "Audio", "Safety"]
  },
  {
    title: "Industrial Safety",
    body:
      "Flag restricted access, unsafe behaviors, and alert escalations.",
    tags: ["Security", "Action", "Compliance"]
  },
  {
    title: "Smart Campus",
    body:
      "Unified dashboards for access control, attendance, and safety events.",
    tags: ["Multi‑site", "Timeline", "Analytics"]
  }
];

export default function DemosPage() {
  return (
    <div className="demos">
      <div className="demos-hero">
        <span className="chip">Demo Scenarios</span>
        <h1>Real‑world applications</h1>
        <p>
          Use Vision V1 across security, attendance, retail, healthcare, and
          industrial safety. Each scenario connects face ID, behavior, action,
          emotion, and audio alerts into a single response flow.
        </p>
      </div>
      <section className="demo-live card">
        <div className="demo-live-head">
          <h2>Security Demo</h2>
          <p>Unknown faces trigger an alert if they remain for 5+ seconds.</p>
        </div>
        <SecurityDemoPanel />
      </section>
      <section className="demo-live card">
        <div className="demo-live-head">
          <h2>Attendance Demo</h2>
          <p>Track known faces and log attendance automatically.</p>
        </div>
        <AttendanceDemoPanel />
      </section>
      <div className="demo-grid">
        {DEMOS.map((item) => (
          <div className="demo-card" key={item.title}>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
            <div className="demo-tags">
              {item.tags.map((tag) => (
                <span className="tag" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
