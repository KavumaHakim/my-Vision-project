const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

export async function faceLast() {
  const res = await fetch(`${BASE}/face/last`);
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "face_last_failed");
  return data;
}

export async function emotionLive() {
  const form = new FormData();
  form.append("source", "live");
  const res = await fetch(`${BASE}/emotion`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "emotion_failed");
  return data;
}

export async function emotionUpload(file) {
  const form = new FormData();
  form.append("source", "upload");
  form.append("file", file);
  const res = await fetch(`${BASE}/emotion`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.detail || "emotion_failed");
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
