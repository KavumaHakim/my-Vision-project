const BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function getHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("health_failed");
  return res.json();
}

export async function getDetections() {
  const res = await fetch(`${BASE}/detections`);
  if (!res.ok) throw new Error("detections_failed");
  return res.json();
}

export async function captureImage() {
  const res = await fetch(`${BASE}/capture`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error || "capture_failed");
  return data;
}

export function streamUrl() {
  return `${BASE}/video-stream`;
}

export function rawStreamUrl(overlay = false) {
  return `${BASE}/raw-stream${overlay ? "?overlay=1" : ""}`;
}

export async function setViewMode(mode) {
  const res = await fetch(`${BASE}/view-mode?mode=${encodeURIComponent(mode)}`, {
    method: "POST",
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "view_mode_failed");
  return data;
}

export async function recordingStart() {
  const res = await fetch(`${BASE}/recording/start`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "recording_start_failed");
  return data;
}

export async function recordingStop() {
  const res = await fetch(`${BASE}/recording/stop`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "recording_stop_failed");
  return data;
}

export async function recordingStatus() {
  const res = await fetch(`${BASE}/recording/status`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "recording_status_failed");
  return data;
}

export async function faceLast() {
  const res = await fetch(`${BASE}/face/last`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "face_last_failed");
  return data;
}

export async function getTimeline(limit = 100) {
  const res = await fetch(`${BASE}/timeline?limit=${limit}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "timeline_failed");
  return data;
}

export async function getActionLast() {
  const res = await fetch(`${BASE}/action/last`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "action_last_failed");
  return data;
}

export async function getAudioLast() {
  const res = await fetch(`${BASE}/audio/last`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "audio_last_failed");
  return data;
}

export async function getPoseLast() {
  const res = await fetch(`${BASE}/pose/last`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "pose_last_failed");
  return data;
}

export async function getSecurityLast() {
  const res = await fetch(`${BASE}/security/last`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "security_last_failed");
  return data;
}

export function securityUnknownFrameUrl(id) {
  const suffix = id ? `?unknown_id=${id}` : "";
  return `${BASE}/security/unknown-frame${suffix}`;
}

export async function getAttendance(limit = 50) {
  const res = await fetch(`${BASE}/attendance?limit=${limit}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "attendance_failed");
  return data;
}

export async function listFaces() {
  const res = await fetch(`${BASE}/faces`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "faces_failed");
  return data;
}

export async function faceRegisterLive(name) {
  const form = new FormData();
  form.append("name", name);
  form.append("source", "live");
  const res = await fetch(`${BASE}/face/register`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "face_register_failed");
  return data;
}

export async function faceRegisterUpload(name, file) {
  const form = new FormData();
  form.append("name", name);
  form.append("source", "upload");
  form.append("file", file);
  const res = await fetch(`${BASE}/face/register`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "face_register_failed");
  return data;
}

export async function faceRecognizeLive() {
  const form = new FormData();
  form.append("source", "live");
  const res = await fetch(`${BASE}/face/recognize`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "face_recognize_failed");
  return data;
}

export async function faceRecognizeUpload(file) {
  const form = new FormData();
  form.append("source", "upload");
  form.append("file", file);
  const res = await fetch(`${BASE}/face/recognize`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "face_recognize_failed");
  return data;
}
