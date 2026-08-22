"use client";
import { useEffect, useRef, useState } from "react";
import { createTimeline, createDrawable, animate, stagger, utils } from "animejs";
import { INDIA_POLY, project } from "@/lib/india";

const VB = 320;
const INDIA_PATH =
  INDIA_POLY.map(([lon, lat], i) => {
    const [x, y] = project(lon, lat, VB, VB);
    return `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ") + " Z";

// scatter a few "pollution" particles inside the bbox
const PARTICLES = Array.from({ length: 26 }, (_, i) => ({
  cx: 60 + ((i * 73) % 220),
  cy: 50 + ((i * 121) % 230),
  r: 1.2 + ((i * 7) % 5) * 0.5,
}));

export function Preloader() {
  const [done, setDone] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const readout = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      animate(root.current!, { opacity: [1, 0], duration: 500, onComplete: () => setDone(true) });
      return;
    }
    const orbit = createDrawable("#pl-orbit");
    const india = createDrawable("#pl-india");
    utils.set("#pl-india", { fillOpacity: 0 });
    utils.set(".pl-particle", { opacity: 0, scale: 0 });

    const setReadout = (s: string) => { if (readout.current) readout.current.textContent = s; };

    const tl = createTimeline({
      defaults: { ease: "inOut(2)" },
      onComplete: () => setDone(true),
    });
    tl.add(orbit, { draw: ["0 0", "0 1"], duration: 750 }, 0)
      .call(() => setReadout("ESTABLISHING ORBIT"), 0)
      .add(india, { draw: ["0 0", "0 1"], duration: 650 }, 600)
      .call(() => setReadout("RESOLVING INDIA"), 600)
      .add("#pl-india", { fillOpacity: [0, 0.12], duration: 600 }, 1150)
      .add(
        ".pl-particle",
        { opacity: [0, 0.9], scale: [0, 1], duration: 700, delay: stagger(18) },
        1100
      )
      .call(() => setReadout("RESOLVING AQI FIELD"), 1200)
      .add(
        ".pl-particle",
        { opacity: 0.35, duration: 600, delay: stagger(10) },
        1900
      )
      .add(root.current!, { opacity: [1, 0], duration: 550, ease: "out(3)" }, 2700);
  }, []);

  if (done) return null;
  return (
    <div
      ref={root}
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center"
      style={{ background: "var(--color-ink-900)" }}
    >
      <svg viewBox={`0 0 ${VB} ${VB}`} width="320" height="320" fill="none">
        <ellipse
          id="pl-orbit"
          cx="160" cy="160" rx="150" ry="78"
          transform="rotate(-18 160 160)"
          stroke="var(--color-signal)" strokeWidth="1" opacity="0.5"
        />
        <path
          id="pl-india"
          d={INDIA_PATH}
          stroke="var(--color-signal)" strokeWidth="1.4"
          fill="var(--color-signal)"
        />
        {PARTICLES.map((p, i) => (
          <circle key={i} className="pl-particle" cx={p.cx} cy={p.cy} r={p.r} fill="#ff7a45" />
        ))}
      </svg>
      <span ref={readout} className="data mt-8 text-[11px]" style={{ color: "var(--color-text-3)", letterSpacing: "0.2em" }}>
        ESTABLISHING ORBIT
      </span>
    </div>
  );
}
