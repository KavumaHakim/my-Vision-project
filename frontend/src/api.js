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
