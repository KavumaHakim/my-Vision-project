import { useEffect, useMemo, useState } from "react";
import {
  getActionLast,
  getAudioLast,
  getDetections,
  getPoseLast,
  getSecurityLast,
  faceLast
} from "../api.js";

function statusPill(active) {
  return active ? "stage-pill active" : "stage-pill";
}

export default function ModelDashboard({ health }) {
  const [snapshot, setSnapshot] = useState({
    detections: null,
    face: null,
    action: null,
    audio: null,
    pose: null,
    security: null
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      const responses = await Promise.allSettled([
        getDetections(),
        faceLast(),
        getActionLast(),
        getAudioLast(),
        getPoseLast(),
        getSecurityLast()
      ]);

      if (!mounted) return;
      const [detections, face, action, audio, pose, security] = responses.map((item) =>
        item.status === "fulfilled" ? item.value : null
      );

      setSnapshot({ detections, face, action, audio, pose, security });
      const failed = responses.some((item) => item.status === "rejected");
      setError(failed ? "Some model feeds are unavailable." : null);
    };

    poll();
    const id = setInterval(poll, 3000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  const modelCards = useMemo(() => {
    const objects = snapshot.detections?.objects || [];
    const faceResult = snapshot.face?.result;
    const actionResult = snapshot.action?.result;
    const audioResult = snapshot.audio?.result;
    const poseResult = snapshot.pose?.result;
    const securityResult = snapshot.security?.result;

    const unknownAlerts = (securityResult?.unknowns || []).filter((item) => item.alerted).length;
    const audioAlert = audioResult?.alert;
    const poses = poseResult?.poses || [];
    const faces = faceResult?.faces || [];

    return [
      {
        name: "Object Detection",
        active: health?.model && objects.length > 0,
        detail: objects.length > 0 ? `${objects.length} objects tracked` : "Waiting for detections"
      },
      {
        name: "Face Recognition",
        active: health?.face_window && faces.length > 0,
        detail: faces.length > 0 ? `${faces.length} face(s) analyzed` : "No active face session"
      },
      {
        name: "Action Tracking",
        active: Boolean(actionResult?.best),
        detail: actionResult?.best
          ? `${actionResult.best.label} (${actionResult.best.score.toFixed(2)})`
          : "No high-confidence action"
      },
      {
        name: "Pose Tracking",
        active: Boolean(snapshot.pose?.enabled && poses.length > 0),
        detail: !snapshot.pose?.enabled
          ? "Pose model not configured"
          : poses.length > 0
            ? `${poses.length} pose(s) tracked`
            : "No pose events"
      },
      {
        name: "Audio Alerts",
        active: Boolean(audioAlert),
        detail: audioAlert
          ? `${audioAlert.label} (${audioAlert.score.toFixed(2)})`
          : "No critical audio signal"
      },
      {
        name: "Security Monitor",
        active: unknownAlerts > 0,
        detail: unknownAlerts > 0 ? `${unknownAlerts} active alert(s)` : "No unknown-face alerts"
      }
    ];
  }, [health, snapshot]);

  const objects = snapshot.detections?.objects || [];
  const personDetected = objects.some((item) => item.label === "person");

  return (
    <div className="model-dashboard">
      <div className="model-dashboard-head">
        <div>
          <h2>Model Dashboard</h2>
          <p className="muted">
            Live orchestration for motion gating, person checks, face recognition, and post-face model execution.
          </p>
        </div>
        <div className={health?.ok ? "pill ok" : "pill"}>{health?.ok ? "Backend Online" : "Backend Offline"}</div>
      </div>

      <div className="pipeline-track">
        <div className={statusPill(Boolean(health?.motion))}>Motion Gate</div>
        <div className={statusPill(Boolean(personDetected || health?.person))}>Person Gate</div>
        <div className={statusPill(Boolean(health?.face_window))}>Face Window</div>
        <div className={statusPill(Boolean(health?.post_face_pipeline))}>Post-Face Pipeline</div>
      </div>

      <div className="model-grid">
        {modelCards.map((card) => (
          <article key={card.name} className={card.active ? "model-card active" : "model-card"}>
            <div className="model-card-head">
              <h3>{card.name}</h3>
              <span className={card.active ? "model-state on" : "model-state"}>{card.active ? "Active" : "Idle"}</span>
            </div>
            <p>{card.detail}</p>
          </article>
        ))}
      </div>

      {error && <div className="error">{error}</div>}
    </div>
  );
}
