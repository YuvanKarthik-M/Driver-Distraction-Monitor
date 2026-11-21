import { useEffect, useRef } from "react";

// Beeps repeatedly while `active` is true. Needs `enabled` (set by a button click)
// because browsers block sound until the user has interacted with the page.
export default function useAlarm(active, enabled, status) {
  const ctxRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;
    if (!ctxRef.current) {
      ctxRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = ctxRef.current;
    if (ctx.state === "suspended") ctx.resume();
    if (!active) return;

    // Higher pitch for closed eyes, lower for looking away.
    const freq = status === "drowsy" ? 1000 : 700;

    const beep = () => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "square";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    };

    beep();
    const id = setInterval(beep, 600);
    return () => clearInterval(id);
  }, [active, enabled, status]);
}