import { useEffect, useState } from "react";
import { getAttendance } from "../api.js";

export default function AttendanceDemoPanel() {
  const [status, setStatus] = useState("idle");
  const [records, setRecords] = useState([]);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      setStatus("loading");
      try {
        const res = await getAttendance(20);
        if (mounted) {
          setRecords(res.records || []);
          setStatus("ready");
        }
      } catch (err) {
        if (mounted) setStatus(err.message || "failed");
      }
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="attendance-demo">
      <div className="muted">Status: {status}</div>
      {records.length === 0 ? (
        <div className="muted">No attendance records yet.</div>
      ) : (
        <ul className="list">
          {records.map((record) => (
            <li key={record.name}>
              <span className="label">{record.name}</span>
              <span className="confidence">{record.total}</span>
              <span className="bbox">Last seen: {record.last_seen}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
