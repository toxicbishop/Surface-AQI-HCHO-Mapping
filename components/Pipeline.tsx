"use client";
import { useEffect, useRef, useState } from "react";
import { createScope, createDrawable, animate, cubicBezier, stagger, utils } from "animejs";

const RESOLVE = cubicBezier(0.16, 1, 0.3, 1);
const DRAW_EASE = cubicBezier(0.65, 0, 0.35, 1);

const INPUTS = [
  { id: "insat", label: "INSAT-3D", sub: "Geostationary AOD · 10 km · 30-min (MOSDAC)" },
  { id: "s5p", label: "Sentinel-5P", sub: "TROPOMI NO₂ SO₂ CO O₃ HCHO columns" },
  { id: "era5", label: "ERA5", sub: "Reanalysis meteorology + boundary-layer height" },
  { id: "cpcb", label: "CPCB", sub: "Ground-station truth · PM2.5 PM10 NO₂ SO₂ O₃ CO" },
  { id: "viirs", label: "VIIRS", sub: "375 m active fire · FRP" },
  { id: "modis", label: "MODIS", sub: "Fire / burned area / EVI" },
];
const STAGES = [
  { id: "fusion", label: "Fusion", x: 360, y: 230, sub: "Co-register all sources onto one grid" },
  { id: "pre", label: "Processing", x: 530, y: 230, sub: "QA filter · regrid · collocate · features" },
  { id: "ml", label: "Random Forest", x: 700, y: 230, sub: "Per-pollutant predictor (deployed) · CNN-LSTM validated, not on map path" },
  { id: "aqi", label: "AQI Maps", x: 900, y: 150, sub: "Surface pollutants → CPCB AQI → daily maps" },
  { id: "hot", label: "Hotspots", x: 900, y: 310, sub: "PHV / Getis-Ord Gi* / DBSCAN detection" },
];
const VBW = 1000, VBH = 460;
const inY = (i: number) => 50 + i * 72;

function edgePath(x1: number, y1: number, x2: number, y2: number) {
  const dx = (x2 - x1) * 0.5;
  return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
}

const EDGES: string[] = [
  ...INPUTS.map((_, i) => edgePath(120, inY(i), 360, 230)),
  edgePath(360, 230, 530, 230),
  edgePath(530, 230, 700, 230),
  edgePath(700, 230, 900, 150),
  edgePath(700, 230, 900, 310),
];

export function Pipeline() {
  const root = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState<{ label: string; sub: string } | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scope = createScope({ root: root.current! }).add(() => {
      utils.set(".pl-node", { opacity: 0, scale: 0.6 });
      if (reduce) { utils.set(".pl-node", { opacity: 1, scale: 1 }); return; }
      const io = new IntersectionObserver((es) => {
        es.forEach((e) => {
          if (!e.isIntersecting) return;
          io.disconnect();
          animate(".pl-node", {
            opacity: [0, 1], scale: [0.6, 1], duration: 500,
            delay: stagger(60), ease: RESOLVE,
          });
          animate(createDrawable(".pl-edge"), {
            draw: ["0 0", "0 1"], duration: 900, delay: stagger(70, { start: 300 }),
            ease: DRAW_EASE,
          });
          animate(".pl-particle", {
            offsetDistance: ["0%", "100%"], duration: 2400, delay: stagger(120),
            loop: true, ease: "linear",
          });
        });
      }, { threshold: 0.25 });
      io.observe(root.current!);
    });
    return () => scope.revert();
  }, []);

  return (
    <div ref={root} className="mt-14">
      <svg viewBox={`0 0 ${VBW} ${VBH}`} className="w-full" style={{ overflow: "visible" }}
        role="img" aria-label="Data pipeline: six observation streams (INSAT-3D, Sentinel-5P, ERA5, CPCB, VIIRS, MODIS) fused, processed, and fed to a Random Forest predictor that produces AQI maps and HCHO hotspots.">
        {/* edges */}
        {EDGES.map((d, i) => (
          <path key={i} className="pl-edge" d={d} fill="none"
            stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
        ))}
        {/* flowing particles */}
        {EDGES.map((d, i) => (
          <circle key={`p${i}`} className="pl-particle" r="2.4" fill="var(--color-signal)"
            style={{ offsetPath: `path('${d}')`, offsetDistance: "0%" } as React.CSSProperties} />
        ))}
        {/* input nodes */}
        {INPUTS.map((n, i) => (
          <g key={n.id} className="pl-node" style={{ cursor: "pointer" }}
            onMouseEnter={() => setActive(n)} onFocus={() => setActive(n)} tabIndex={0}
            role="img" aria-label={`${n.label}: ${n.sub}`}>
            <circle cx="120" cy={inY(i)} r="6" fill="none" stroke="var(--color-signal)" strokeWidth="1.4" />
            <text x="104" y={inY(i) + 4} textAnchor="end" className="data" fontSize="13"
              fill="var(--color-text-1)">{n.label}</text>
          </g>
        ))}
        {/* stage nodes */}
        {STAGES.map((s) => (
          <g key={s.id} className="pl-node" style={{ cursor: "pointer" }}
            onMouseEnter={() => setActive(s)} onFocus={() => setActive(s)} tabIndex={0}
            role="img" aria-label={`${s.label}: ${s.sub}`}>
            <rect x={s.x - 62} y={s.y - 19} width="124" height="38" rx="4"
              fill="var(--color-ink-700)" stroke="rgba(255,255,255,0.18)" strokeWidth="1" />
            <text x={s.x} y={s.y + 4} textAnchor="middle" className="data" fontSize="13"
              fill="var(--color-text-1)">{s.label}</text>
          </g>
        ))}
      </svg>
      <div className="hairline data mt-4 min-h-[44px] border-t pt-4 text-[13px]"
        style={{ color: "var(--color-text-2)" }}>
        {active ? (
          <><span style={{ color: "var(--color-signal)" }}>{active.label}</span> — {active.sub}</>
        ) : (
          <span style={{ color: "var(--color-text-3)" }}>Hover a node to inspect the data flow.</span>
        )}
      </div>
    </div>
  );
}
