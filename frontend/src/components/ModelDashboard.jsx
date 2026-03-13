import { useEffect, useMemo, useState } from "react";
import {
  getActionLast,
  getAudioLast,
  getCrowdLast,
  getDetections,
  getModelToggles,
  getPoseLast,
  getSecurityLast,
  faceLast,
  updateModelToggles
} from "../api.js";

function statusPill(active) {
  return active ? "stage-pill active" : "stage-pill";
}

const TOGGLE_META = [
  { key: "object_detection", label: "Object Detection" },
  { key: "face_recognition", label: "Face Recognition" },
  { key: "emotion", label: "Emotion" },
  { key: "action_tracking", label: "Action Tracking" },
  { key: "pose_tracking", label: "Pose Tracking" },
  { key: "audio_alerts", label: "Audio Alerts" },
  { key: "crowd_analysis", label: "Crowd Analysis" }
];

export default function ModelDashboard({ health }) {
  const [snapshot, setSnapshot] = useState({
    detections: null,
    face: null,
    action: null,
    audio: null,
    pose: null,
    security: null,
    crowd: null
  });
  const [toggles, setToggles] = useState(health?.model_toggles || null);
  const [busyToggle, setBusyToggle] = useState(null);
  const [error, setError] = useState(null);
  const defaultToggleState = useMemo(
    () => Object.fromEntries(TOGGLE_META.map((item) => [item.key, true])),
    []
  );

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      const responses = await Promise.allSettled([
        getDetections(),
        faceLast(),
        getActionLast(),
        getAudioLast(),
        getPoseLast(),
        getSecurityLast(),
        getCrowdLast(),
        getModelToggles()
      ]);

      if (!mounted) return;
      const [detections, face, action, audio, pose, security, crowd, modelToggles] = responses.map((item) =>
        item.status === "fulfilled" ? item.value : null
      );

      setSnapshot({ detections, face, action, audio, pose, security, crowd });
      if (modelToggles?.toggles) setToggles(modelToggles.toggles);
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

  const handleToggle = async (key, nextValue) => {
    if (!toggles) return;
    const previous = toggles;
    setBusyToggle(key);
    setToggles({ ...toggles, [key]: nextValue });
    try {
      const updated = await updateModelToggles({ [key]: nextValue });
      setToggles(updated?.toggles || { ...previous, [key]: nextValue });
      setError(null);
    } catch (err) {
      setToggles(previous);
      setError(err.message || "Failed to update model toggle.");
    } finally {
      setBusyToggle(null);
    }
  };

  const modelCards = useMemo(() => {
    const gate = toggles || defaultToggleState;
    const objects = snapshot.detections?.objects || [];
    const faceResult = snapshot.face?.result;
    const actionResult = snapshot.action?.result;
    const audioResult = snapshot.audio?.result;
    const poseResult = snapshot.pose?.result;
    const securityResult = snapshot.security?.result;
    const crowdResult = snapshot.crowd?.result;

    const unknownAlerts = (securityResult?.unknowns || []).filter((item) => item.alerted).length;
    const audioAlert = audioResult?.alert;
    const poses = poseResult?.poses || [];
    const poseAction = poseResult?.best_action;
    const faces = faceResult?.faces || [];
    const crowdRisk = crowdResult?.crowd?.risk;
    const crowdLevel = crowdResult?.crowd?.level;
    const crowdPeople = crowdResult?.people?.estimate ?? 0;

    return [
      {
        name: "Object Detection",
        active: Boolean(gate.object_detection && health?.model && objects.length > 0),
        detail: !gate.object_detection
          ? "Disabled by user toggle"
          : objects.length > 0
          ? `${objects.length} objects tracked`
          : "Waiting for detections"
      },
      {
        name: "Face Recognition",
        active: Boolean(gate.face_recognition && health?.face_window && faces.length > 0),
        detail: !gate.face_recognition
          ? "Disabled by user toggle"
          : faces.length > 0
          ? `${faces.length} face(s) analyzed`
          : "No active face session"
      },
      {
        name: "Action Tracking",
        active: Boolean(gate.action_tracking && actionResult?.best),
        detail: !gate.action_tracking
          ? "Disabled by user toggle"
          : actionResult?.best
          ? `${actionResult.best.label} (${actionResult.best.score.toFixed(2)})`
          : "No high-confidence action"
      },
      {
        name: "Pose Tracking",
        active: Boolean(gate.pose_tracking && snapshot.pose?.enabled && (poses.length > 0 || poseAction)),
        detail: !gate.pose_tracking
          ? "Disabled by user toggle"
          : !snapshot.pose?.enabled
          ? "Pose model not configured"
          : poseAction
            ? `${poseAction.label} (${poseAction.score.toFixed(2)})`
            : poses.length > 0
            ? `${poses.length} pose(s) tracked`
            : "No pose events"
      },
      {
        name: "Audio Alerts",
        active: Boolean(gate.audio_alerts && audioAlert),
        detail: !gate.audio_alerts
          ? "Disabled by user toggle"
          : audioAlert
          ? `${audioAlert.label} (${audioAlert.score.toFixed(2)})`
          : "No critical audio signal"
      },
      {
        name: "Security Monitor",
        active: unknownAlerts > 0,
        detail: unknownAlerts > 0 ? `${unknownAlerts} active alert(s)` : "No unknown-face alerts"
      },
      {
        name: "Crowd Analysis",
        active: Boolean(gate.crowd_analysis && crowdResult && crowdRisk && crowdRisk !== "normal"),
        detail: !gate.crowd_analysis
          ? "Disabled by user toggle"
          : crowdResult
          ? `${crowdLevel || "none"} crowd, ${crowdPeople} people, risk ${crowdRisk || "normal"}`
          : "Waiting for crowd metrics"
      }
    ];
  }, [health, snapshot, toggles, defaultToggleState]);

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

      <div className="model-toggle-grid">
        {TOGGLE_META.map((item) => {
          const checked = Boolean((toggles || defaultToggleState)[item.key]);
          const disabled = busyToggle !== null || (item.key === "pose_tracking" && !health?.pose_enabled);
          return (
            <label key={item.key} className={checked ? "model-toggle active" : "model-toggle"}>
              <span>{item.label}</span>
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={(event) => handleToggle(item.key, event.target.checked)}
              />
            </label>
          );
        })}
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
