import { useEffect, useRef, useState } from "react";
import StatusPanel from "./StatusPanel.jsx";
import SessionSummary from "./SessionSummary.jsx";
import EventLog from "./EventLog.jsx";
import useAlarm from "./useAlarm.js";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";
const EMPTY = {
  monitoredMs: 0, awayMs: 0, closedMs: 0,
  awayCount: 0, closedCount: 0, longestMs: 0, runMs: 0,
};

export default function App() {
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const waitingRef = useRef(false);

  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(true);
  const [error, setError] = useState("");
  const [events, setEvents] = useState([]);
  const [alarmOn, setAlarmOn] = useState(false);

  // Session numbers live in refs and are advanced by one steady clock (below),
  // so they do not depend on how fast frames come back from the backend.
  const acc = useRef({ ...EMPTY });
  const [stats, setStats] = useState({ ...EMPTY });
  const lastStatus = useRef("ok");
  const calibratingRef = useRef(true);

  const runningRef = useRef(running);
  const connectedRef = useRef(connected);
  runningRef.current = running;
  connectedRef.current = connected;

  // Backend connection (once).
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      waitingRef.current = false;
      if (runningRef.current) setData(JSON.parse(e.data));
    };
    return () => ws.close();
  }, []);

  // Camera + frame sending. Runs only while monitoring is on.
  useEffect(() => {
    if (!running) return;
    let timer, stream, stopped = false;
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 240;

    function sendFrame() {
      const ws = wsRef.current;
      const v = videoRef.current;
      if (!ws || ws.readyState !== 1 || waitingRef.current || !v || !v.videoWidth) return;
      canvas.getContext("2d").drawImage(v, 0, 0, 320, 240);
      waitingRef.current = true;
      canvas.toBlob((b) => b && ws.send(b), "image/jpeg", 0.6);
    }

    async function start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      } catch {
        setError("Camera access was blocked. Allow the camera in your browser and try again.");
        setRunning(false);
        return;
      }
      if (stopped) return stream.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = stream;
      waitingRef.current = false;
      const ws = wsRef.current;
      if (ws && ws.readyState === 1) ws.send("recalibrate"); // fresh calibration on every start
      timer = setInterval(sendFrame, 100);
    }

    start();
    return () => {
      stopped = true;
      clearInterval(timer);
      if (stream) stream.getTracks().forEach((t) => t.stop()); // turns the camera light off
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, [running]);

  // Status changes: count events and fill the event log.
  useEffect(() => {
    if (!data) return;
    calibratingRef.current = data.calibrating;
    const prev = lastStatus.current;
    const cur = data.status;
    if (cur === prev) return;
    lastStatus.current = cur;
    acc.current.runMs = 0;
    if (cur === "looking_away") acc.current.awayCount += 1;
    if (cur === "drowsy") acc.current.closedCount += 1;
    if (cur !== "ok") {
      setEvents((ev) => [{ time: new Date().toLocaleTimeString(), status: cur }, ...ev].slice(0, 50));
    }
  }, [data]);

  // One steady clock for all session timing.
  useEffect(() => {
    let last = performance.now();
    const id = setInterval(() => {
      const now = performance.now();
      const dt = Math.min(now - last, 1000); // a stalled tab never adds a huge jump
      last = now;
      const a = acc.current;
      // Time only counts while monitoring is on, the backend is connected,
      // and calibration is finished.
      if (runningRef.current && connectedRef.current && !calibratingRef.current) {
        a.monitoredMs += dt;
        const st = lastStatus.current;
        if (st === "looking_away") a.awayMs += dt;
        if (st === "drowsy") a.closedMs += dt;
        if (st !== "ok") {
          a.runMs += dt;
          a.longestMs = Math.max(a.longestMs, a.runMs);
        }
      }
      setStats({ ...a });
    }, 250);
    return () => clearInterval(id);
  }, []);

  function toggleRunning() {
    if (running) {
      setRunning(false);
      setData(null);
      lastStatus.current = "ok";
      calibratingRef.current = true;
      acc.current.runMs = 0;
    } else {
      setError("");
      setRunning(true);
    }
  }

  function recalibrate() {
    const ws = wsRef.current;
    if (ws && ws.readyState === 1) ws.send("recalibrate");
  }

  function resetSummary() {
    acc.current = { ...EMPTY };
    setStats({ ...EMPTY });
    setEvents([]);
  }

  const alert = running && data && data.status !== "ok";
  useAlarm(!!alert, alarmOn, data ? data.status : "ok");

  return (
    <main className="page">
      <header className="top">
        <h1>Driver monitor</h1>
        <div className="actions">
          <button className="alarm-btn" onClick={toggleRunning}>
            {running ? "Stop" : "Start"}
          </button>
          <button className="alarm-btn" onClick={recalibrate} disabled={!connected || !running}>
            Recalibrate
          </button>
          <button className={"alarm-btn" + (alarmOn ? " on" : "")} onClick={() => setAlarmOn((v) => !v)}>
            {alarmOn ? "Alarm on" : "Turn alarm on"}
          </button>
        </div>
      </header>
      {error && <p className="error">{error}</p>}
      <div className="grid">
        <div className={"video-wrap" + (alert ? " alert" : "")}>
          <video ref={videoRef} autoPlay playsInline muted />
          {!running && <div className="paused">Monitoring stopped</div>}
        </div>
        <div className="side">
          <StatusPanel data={data} connected={connected} paused={!running} />
          <SessionSummary stats={stats} running={running} onReset={resetSummary} />
        </div>
      </div>
      <EventLog events={events} />
      <p className="note">
        Your camera video is sent to the server for analysis only. It is not recorded or stored.
      </p>
    </main>
  );
}