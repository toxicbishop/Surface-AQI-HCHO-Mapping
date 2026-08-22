"use client";
import { useEffect, useRef, useState } from "react";
import { animate, cubicBezier } from "animejs";
import { Section } from "./Section";
import { IndiaField } from "./IndiaField";
import { DeckMap } from "./DeckMap";
import { useDrawOnEnter } from "@/lib/useDrawOnEnter";
import { INDIA_POLY, project, AQI_STOPS, PLACES } from "@/lib/india";

/* ---------- shared helpers ---------- */
const MVW = 600, MVH = 620;
const RESOLVE = cubicBezier(0.16, 1, 0.3, 1);
const indiaD =
  INDIA_POLY.map(([lon, lat], i) => {
    const [x, y] = project(lon, lat, MVW, MVH);
    return `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ") + " Z";
const place = (k: keyof typeof PLACES, w = MVW, h = MVH) => project(PLACES[k][0], PLACES[k][1], w, h);

function CountUp({ to, decimals = 2, suffix = "" }: { to: number; decimals?: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const obj = { v: 0 };
    const render = () => { el.textContent = obj.v.toFixed(decimals) + suffix; };
    if (reduce) { obj.v = to; render(); return; }
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        animate(obj, { v: to, duration: 1200, ease: "out(3)", onUpdate: render });
      }), { threshold: 0.5 });
    io.observe(el);
    return () => io.disconnect();
  }, [to, decimals, suffix]);
  return <span ref={ref} className="data">{(0).toFixed(decimals) + suffix}</span>;
}

function AqiLegend() {
  return (
    <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2">
      {AQI_STOPS.map((s) => (
        <div key={s.label} className="flex items-center gap-2">
          <span className="block h-3 w-3 rounded-sm" style={{ background: s.color }} />
          <span className="data text-[11px]" style={{ color: "var(--color-text-2)" }}>{s.label}</span>
        </div>
      ))}
    </div>
  );
}

/* ====================================================== 02 · MISSION SNAPSHOT */
const SNAPSHOT = [
  ["Highest AQI Region", "Delhi NCR", "Very Poor risk corridor"],
  ["Strongest HCHO Hotspot", "Western UP", "VOC anomaly cluster"],
  ["Fire-linked Hotspots", "91", "real MODIS-attributed HCHO clusters"],
  ["Dominant Pollutant", "PM2.5", "aerosol-driven AQI signal"],
  ["Transport Risk", "High", "Punjab/Haryana -> Delhi NCR pathway"],
  ["Data Status", "Real + validated", "TROPOMI/MODIS observed · AQI validated vs 161 CPCB stations"],
];

export function MissionSnapshot() {
  return (
    <Section id="mission-snapshot" index="02" eyebrow="Mission Snapshot"
      title="Today's atmospheric intelligence."
      lede="A judge-facing snapshot of how VAYU converts satellite observations, fire activity and atmospheric transport into AQI and HCHO hotspot intelligence.">
      <div className="mt-8 inline-flex max-w-full flex-wrap gap-2 rounded-sm border px-3 py-2 data text-[11px]"
        style={{ borderColor: "var(--line)", color: "var(--color-text-2)", background: "rgba(255,255,255,0.03)" }}>
        <span style={{ color: "var(--color-signal)" }}>Real TROPOMI · MODIS Layers</span>
        <span>Post-monsoon · India</span>
        <span>AQI = RF model, CPCB-validated (random-CV R² 0.53–0.71)</span>
      </div>
      <div className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-sm border sm:grid-cols-2 lg:grid-cols-3"
        style={{ borderColor: "var(--line)", background: "var(--line)" }}>
        {SNAPSHOT.map(([label, value, sub]) => (
          <div key={label} data-reveal className="metric-card">
            <div className="data text-[10px] uppercase" style={{ color: "var(--color-text-3)", letterSpacing: "0.14em" }}>{label}</div>
            <div className="serif mt-4 text-[clamp(1.9rem,3vw,3rem)] leading-none">{value}</div>
            <div className="data mt-3 text-[12px]" style={{ color: "var(--color-text-2)" }}>{sub}</div>
          </div>
        ))}
      </div>
      <div className="mt-8 grid grid-cols-1 gap-4 border-t pt-6 md:grid-cols-[0.7fr_1.3fr]"
        style={{ borderColor: "var(--line)" }}>
        <a href="/problem" className="data inline-flex w-fit items-center rounded-full px-5 py-2 text-[12px]"
          style={{ border: "1px solid var(--color-signal)", color: "var(--color-signal)" }}>
          Start 90-second demo
        </a>
        <div className="data text-[12px] leading-7" style={{ color: "var(--color-text-2)" }}>
          <span style={{ color: "var(--color-text-1)" }}>Demo script:</span> 1. monitoring gap · 2. satellite signals ·
          3. AQI layer · 4. HCHO hotspots · 5. fire activity · 6. wind transport · 7. policy action
        </div>
      </div>
    </Section>
  );
}

/* ====================================================== 02 · WHAT IS AIR QUALITY */
const POLLUTANTS = [
  { k: "PM2.5", src: "Combustion · vehicles · secondary aerosol", h: "Penetrates deep into lungs & bloodstream", inf: 96 },
  { k: "PM10", src: "Dust · construction · road resuspension", h: "Aggravates respiratory disease", inf: 84 },
  { k: "NO₂", src: "Traffic · power generation", h: "Inflames airways; forms ozone & PM", inf: 78 },
  { k: "SO₂", src: "Coal combustion · smelting", h: "Triggers asthma; acid aerosols", inf: 52 },
  { k: "CO", src: "Incomplete combustion · fires", h: "Reduces blood oxygen capacity", inf: 48 },
  { k: "O₃", src: "Photochemical (NOₓ + VOCs + sun)", h: "Damages lung tissue at ground level", inf: 66 },
];
export function AirQuality() {
  return (
    <Section id="air-quality" index="01" eyebrow="The Metric" variant="paper" grid
      title="Air quality, made of six numbers."
      lede="The Air Quality Index folds many pollutants into a single value — the worst sub-index governs. Each pollutant has a source, a health cost, and a different weight in what you breathe.">
      <div className="mt-14 divide-y" style={{ borderColor: "rgba(0,0,0,0.12)" }}>
        {POLLUTANTS.map((p) => (
          <div key={p.k} data-reveal className="grid grid-cols-12 items-center gap-4 py-6"
            style={{ borderTop: "1px solid rgba(0,0,0,0.12)" }}>
            <div className="col-span-12 md:col-span-2 serif text-2xl">{p.k}</div>
            <div className="col-span-6 md:col-span-4 text-[14px]" style={{ color: "#4a525b" }}>{p.src}</div>
            <div className="col-span-6 md:col-span-4 text-[14px]" style={{ color: "#4a525b" }}>{p.h}</div>
            <div className="col-span-12 md:col-span-2">
              <div className="h-1.5 w-full rounded-full" style={{ background: "rgba(0,0,0,0.08)" }}>
                <div className="h-full rounded-full" style={{ width: `${p.inf}%`, background: "var(--color-signal-dim)" }} />
              </div>
              <div className="data mt-1 text-[10px]" style={{ color: "#8a857a" }}>AQI INFLUENCE {p.inf}</div>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ====================================================== 04 · OBSERVATION SIGNALS */
const SIGNALS = [
  ["INSAT-3D AOD", "Aerosol signal", "MOSDAC / ISRO", "10 km, high-frequency geostationary observation", "AOD is not direct surface PM2.5; meteorology is needed for conversion."],
  ["Sentinel-5P HCHO", "VOC precursor signal", "TROPOMI", "Satellite column observation", "HCHO column is not direct surface VOC concentration."],
  ["Sentinel-5P NO2 / SO2 / CO / O3", "Trace-gas context", "TROPOMI", "Column and tropospheric products", "Surface conversion requires ground validation and meteorology."],
  ["CPCB CAAQMS", "Ground truth", "CPCB", "Station-level surface measurements", "Sparse and unevenly distributed across India."],
  ["ERA5 / IMDAA", "Transport and dispersion", "Reanalysis meteorology", "Grid-scale meteorological fields", "Approximate for local plume movement."],
  ["MODIS / VIIRS Fire", "Biomass-burning evidence", "NASA FIRMS", "Active fire and FRP signal", "Fire-HCHO correlation does not prove causality alone."],
];

export function Signals() {
  return (
    <Section id="signals" index="01" eyebrow="Observation Stack" variant="paper" grid
      title="Six signals, measured separately."
      lede="Every layer is treated as a separate atmospheric signal before it is fused into AQI, HCHO hotspot and transport intelligence.">
      <div className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-sm border md:grid-cols-2"
        style={{ borderColor: "rgba(0,0,0,0.12)", background: "rgba(0,0,0,0.12)" }}>
        {SIGNALS.map(([name, role, source, precision, limitation]) => (
          <div key={name} data-reveal className="evidence-card panel-paper">
            <div className="flex items-start justify-between gap-4">
              <h3 className="serif text-2xl leading-tight">{name}</h3>
              <span className="status-badge">{role}</span>
            </div>
            <dl className="mt-6 grid gap-4 data text-[12px]">
              <div>
                <dt>Source</dt>
                <dd>{source}</dd>
              </div>
              <div>
                <dt>Precision</dt>
                <dd>{precision}</dd>
              </div>
              <div>
                <dt>Limitation</dt>
                <dd>{limitation}</dd>
              </div>
            </dl>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ====================================================== 03 · WHY SATELLITES */
export function WhySatellites() {
  const ref = useDrawOnEnter<HTMLDivElement>(".draw");
  const stations = Array.from({ length: 16 }, (_, i) => {
    const pts: [number, number][] = [
      place("delhi"), place("mumbai"), place("kolkata"), place("chennai"),
      place("bengaluru"), place("hyderabad"), place("lucknow"), place("ahmedabad"),
      [320, 220], [360, 300], [280, 360], [400, 200], [250, 250], [430, 360], [330, 150], [300, 430],
    ];
    return pts[i];
  });
  return (
    <Section id="satellites" index="01" eyebrow="The Gap"
      title="Most people live far beyond a monitor."
      lede="India's ground network is sparse. Satellites see the whole sky, every day — turning a handful of points into a national field.">
      <div className="mt-12 grid grid-cols-12 items-center gap-10">
        <div ref={ref} className="col-span-12 md:col-span-7">
          <svg viewBox={`0 0 ${MVW} ${MVH}`} className="w-full">
            <path className="draw" d={indiaD} fill="none" stroke="var(--color-signal)" strokeWidth="1.4" />
            <path d={indiaD} fill="var(--color-signal)" fillOpacity="0.05" />
            {stations.map(([x, y], i) => (
              <circle key={i} cx={x} cy={y} r="3" fill="var(--color-signal)" opacity="0.85" />
            ))}
          </svg>
        </div>
        <div className="col-span-12 md:col-span-5">
          <div className="serif text-[clamp(2.5rem,5vw,4rem)]"><CountUp to={161} decimals={0} suffix="" /></div>
          <p className="data mt-1 text-[13px]" style={{ color: "var(--color-text-2)" }}>CPCB stations validated against</p>
          <div className="mt-8 serif text-[clamp(2.5rem,5vw,4rem)]"><CountUp to={1.4} decimals={1} suffix="B" /></div>
          <p className="data mt-1 text-[13px]" style={{ color: "var(--color-text-2)" }}>people to cover</p>
        </div>
      </div>
    </Section>
  );
}

/* ====================================================== 04 · DATA PIPELINE handled by Pipeline.tsx */

/* ====================================================== 05 · SATELLITE OBSERVATIONS */
const LAYERS = [
  { k: "AOD", g: "aod", u: "unitless" }, { k: "NO₂", g: "no2", u: "mol/m²" },
  { k: "CO", g: "co", u: "mol/m²" }, { k: "SO₂", g: "so2", u: "mol/m²" },
  { k: "O₃", g: "o3", u: "mol/m²" }, { k: "HCHO", g: "hcho", u: "mol/m²" },
];
export function Observations() {
  const [active, setActive] = useState(5);
  return (
    <Section id="observations" index="02" eyebrow="The Instruments"
      title="What the satellites see."
      lede="The seasonal-mean column of each trace gas over India, rendered with MapLibre + deck.gl. Switch layers to compare what each instrument measures.">
      <div className="mt-10 flex flex-wrap gap-2">
        {LAYERS.map((l, i) => (
          <button key={l.k} onClick={() => setActive(i)}
            className="data rounded-full px-4 py-2 text-[12px] transition-colors"
            style={{
              border: "1px solid " + (i === active ? "var(--color-signal)" : "rgba(255,255,255,0.14)"),
              color: i === active ? "var(--color-signal)" : "var(--color-text-2)",
            }}>{l.k}</button>
        ))}
      </div>
      <div className="mt-8" role="img"
        aria-label={`Seasonal-mean ${LAYERS[active].k} tropospheric column over India, rendered with MapLibre and deck.gl; values normalised 0 to 1.`}>
        <DeckMap mode="gas" gas={LAYERS[active].g} height={520} />
      </div>
      <div className="hairline data mt-4 border-t pt-4 text-[13px]" style={{ color: "var(--color-text-2)" }}>
        <span style={{ color: "var(--color-signal)" }}>{LAYERS[active].k}</span> · tropospheric column ·
        normalised 0–1 (2–98th percentile) · OFFL L3 · qa-screened
      </div>
    </Section>
  );
}

/* ====================================================== 06 · AQI OVER INDIA (flagship) */
export function AQIIndia() {
  const [frame, setFrame] = useState(0);
  const [nframes, setNframes] = useState(0); // actual frame count from loaded data
  const [playing, setPlaying] = useState(true);
  const [readout, setReadout] = useState<string | null>(null);
  const [view, setView] = useState<"cpcb" | "rapi" | "zones">("cpcb");
  const anim = useRef<ReturnType<typeof animate> | null>(null);
  const obj = useRef({ f: 0 });
  const playingRef = useRef(true);
  const wrapRef = useRef<HTMLDivElement>(null);

  const multi = view !== "zones" && nframes > 1; // only AQI data with multiple frames gets a scrubber

  useEffect(() => {
    if (!multi) { anim.current?.cancel(); anim.current = null; setFrame(0); return; }
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setPlaying(false); playingRef.current = false; }
    // Anime.js drives the timelapse frame; plays only while the section is in view.
    anim.current = animate(obj.current, {
      f: [0, nframes - 1], duration: 9000, ease: "linear", loop: true, autoplay: false,
      onUpdate: () => setFrame(Math.round(obj.current.f)),
    });
    if (!reduce && playingRef.current) {
      const io = new IntersectionObserver(
        (es) => es.forEach((e) => {
          if (e.isIntersecting && playingRef.current) anim.current?.play();
          else anim.current?.pause();
        }), { threshold: 0.3 });
      if (wrapRef.current) io.observe(wrapRef.current);
      return () => { io.disconnect(); anim.current?.cancel(); };
    }
    return () => { anim.current?.cancel(); };
  }, [multi, nframes]);

  const toggle = () => {
    const np = !playingRef.current;
    playingRef.current = np; setPlaying(np);
    if (np) anim.current?.play(); else anim.current?.pause();
  };
  const onSlider = (v: number) => {
    obj.current.f = v; setFrame(v);
    playingRef.current = false; setPlaying(false); anim.current?.pause();
  };

  return (
    <Section id="aqi" index="03" eyebrow="The Picture"
      title="India, breathing."
      lede="A real surface-AQI field — predicted by the Random Forest on the gridded satellite stack, coloured by the CPCB scale, rendered live with MapLibre + deck.gl. Hover any cell to read its value.">
      <div className="mt-8 flex flex-wrap items-center gap-2">
        {(["cpcb", "rapi", "zones"] as const).map((k) => (
          <button key={k} onClick={() => setView(k)}
            aria-pressed={view === k}
            className="data rounded-full px-4 py-2 text-[12px] uppercase transition-colors"
            style={{
              border: "1px solid " + (view === k ? "var(--color-signal)" : "rgba(255,255,255,0.14)"),
              color: view === k ? "var(--color-signal)" : "var(--color-text-2)",
            }}>{k === "cpcb" ? "CPCB AQI" : k === "rapi" ? "RAPI" : "K-Means zones"}</button>
        ))}
        <span className="data text-[11px]" style={{ color: "var(--color-text-3)" }}>
          {view === "cpcb" ? "Official CPCB national index" : view === "rapi" ? "Entropy-weighted model comparison index" : "Relative pollution-character clusters"}
        </span>
      </div>
      <div ref={wrapRef} className="mt-6"
        aria-label="Interactive surface-AQI map of India rendered with MapLibre and deck.gl. Use the CPCB / RAPI toggle and hover cells for values.">
        <DeckMap mode={view === "zones" ? "zones" : "aqi"} frame={frame}
          aqiKind={view === "rapi" ? "rapi" : "cpcb"} height={560}
          onReadout={setReadout} onFrameCount={view === "zones" ? undefined : setNframes} />
      </div>
      <div className="mt-6 flex items-center gap-4">
        {multi && (
          <>
            <button onClick={toggle} aria-label={playing ? "Pause timelapse" : "Play timelapse"}
              className="data text-[12px]"
              style={{ border: "1px solid var(--color-signal)", color: "var(--color-signal)", borderRadius: 9999, padding: "4px 12px" }}>
              {playing ? "❚❚ Pause" : "▶ Play"}
            </button>
            <span className="data text-[12px]" style={{ color: "var(--color-signal)" }}>FRAME {frame + 1}/{nframes}</span>
            <input aria-label="Time frame" type="range" min={0} max={nframes - 1} step={1}
              value={frame} onChange={(e) => onSlider(parseInt(e.target.value))}
              className="h-1 flex-1 cursor-pointer appearance-none rounded-full"
              style={{ background: "linear-gradient(90deg, var(--color-signal-dim), var(--color-signal))" }} />
          </>
        )}
        {!multi && (
          <span className="data text-[12px]" style={{ color: "var(--color-text-3)" }}>
            Single daily composite — no timelapse for this dataset.
          </span>
        )}
        <span className="data text-[12px]" style={{ color: "var(--color-text-3)" }}>{readout ?? (view === "zones" ? "hover a zone" : "hover a cell")}</span>
      </div>
      <AqiLegend />
    </Section>
  );
}

/* ====================================================== 07 · UNDERSTANDING HCHO */
export function HCHO() {
  const ref = useDrawOnEnter<HTMLDivElement>(".draw");
  const Node = ({ x, label }: { x: number; label: string }) => (
    <g>
      <circle cx={x} cy="60" r="26" fill="var(--color-paper)" stroke="var(--color-signal-dim)" strokeWidth="1.4" />
      <text x={x} y="64" textAnchor="middle" className="data" fontSize="13" fill="var(--color-paper-ink)">{label}</text>
    </g>
  );
  return (
    <Section id="hcho" index="04" eyebrow="The Molecule" variant="paper"
      title="Formaldehyde is the air turning reactive."
      lede="HCHO is a short-lived product of VOC oxidation — a fingerprint of emissions and biomass burning, and a precursor that helps build ground-level ozone.">
      <div ref={ref} className="mt-12">
        <svg viewBox="0 0 720 130" className="w-full max-w-[760px]">
          <Node x={70} label="VOCs" />
          <Node x={300} label="HCHO" />
          <Node x={540} label="O₃" />
          <path className="draw" d="M 100 60 L 270 60" stroke="var(--color-signal-dim)" strokeWidth="1.4" fill="none" markerEnd="url(#a)" />
          <path className="draw" d="M 330 60 L 510 60" stroke="var(--color-signal-dim)" strokeWidth="1.4" fill="none" markerEnd="url(#a)" />
          <path className="draw" d="M 300 110 L 300 90" stroke="var(--color-ember)" strokeWidth="1.4" fill="none" markerEnd="url(#b)" />
          <text x="185" y="48" textAnchor="middle" className="data" fontSize="11" fill="#8a857a">+ OH</text>
          <text x="420" y="48" textAnchor="middle" className="data" fontSize="11" fill="#8a857a">+ sunlight, NOₓ</text>
          <text x="300" y="126" textAnchor="middle" className="data" fontSize="11" fill="var(--color-ember)">biomass burning</text>
          <defs>
            <marker id="a" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 z" fill="var(--color-signal-dim)" /></marker>
            <marker id="b" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 z" fill="var(--color-ember)" /></marker>
          </defs>
        </svg>
      </div>
    </Section>
  );
}

/* ====================================================== 08 · HCHO HOTSPOTS */
export function Hotspots() {
  const [readout, setReadout] = useState<string | null>(null);
  const [method, setMethod] = useState<"phv" | "isolation">("phv");
  const legend: [string, string][] = [
    ["agri_burning", "#ff7a45"], ["urban", "#a78bfa"], ["industrial", "#f2a93b"],
    ["biogenic", "#7fbf7f"], ["other", "#969ca4"],
  ];
  return (
    <Section id="hotspots" index="04" eyebrow="The Finding"
      title="Where the air turns reactive."
      lede={method === "phv"
        ? "PHV anomalies are grouped into connected regions and attributed to a source hypothesis over a seasonal HCHO basemap."
        : "Isolation Forest flags unusual HCHO/NO₂/CO feature vectors as a comparative anomaly baseline; it is not a confirmed source label."}
    >
      <div className="mt-8 flex flex-wrap gap-2">
        {(["phv", "isolation"] as const).map((k) => (
          <button key={k} onClick={() => setMethod(k)} aria-pressed={method === k}
            className="data rounded-full px-4 py-2 text-[12px] uppercase transition-colors"
            style={{ border: "1px solid " + (method === k ? "var(--color-signal)" : "rgba(255,255,255,0.14)"), color: method === k ? "var(--color-signal)" : "var(--color-text-2)" }}>
            {k === "phv" ? "PHV + attribution" : "Isolation Forest comparison"}
          </button>
        ))}
      </div>
      <div className="mt-8" role="img"
        aria-label={method === "phv" ? "Map of PHV HCHO hotspots over India, grouped and coloured by source hypothesis." : "Map of HCHO anomalies flagged by Isolation Forest over India; anomalies are not confirmed emission sources."}>
        <DeckMap mode={method === "phv" ? "hotspots" : "isolation"} height={560} onReadout={setReadout} />
      </div>
      <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 data text-[12px]" style={{ color: "var(--color-text-2)" }}>
        {method === "phv" && legend.map(([k, c]) => (
          <span key={k} className="flex items-center gap-2">
            <span className="block h-2.5 w-2.5 rounded-full" style={{ background: c }} />{k}
          </span>
        ))}
        {method === "isolation" && <span className="flex items-center gap-2"><span className="block h-2.5 w-2.5 rounded-full" style={{ background: "#ff7a45" }} />anomaly cluster</span>}
        <span style={{ color: "var(--color-text-3)" }}>{readout ?? (method === "phv" ? "sample attributed hotspots" : "Isolation Forest anomaly score")}</span>
      </div>
    </Section>
  );
}

/* ====================================================== 09 · BIOMASS BURNING */
const BURN_STATES = [
  {
    label: "Before burning",
    season: 0.35,
    text: "Background HCHO and PM2.5 remain closer to seasonal baseline. Fire pixels are sparse and attribution should stay conservative.",
    metrics: ["Fire signal low", "HCHO baseline", "AQI watch"],
  },
  {
    label: "During burning",
    season: 0.9,
    text: "Fire clusters intensify across agricultural belts. CO, aerosols and HCHO anomaly signals rise in the same regional window.",
    metrics: ["Fire signal high", "HCHO rising", "AQI pressure"],
  },
  {
    label: "After burning",
    season: 0.68,
    text: "Downwind regions may show delayed HCHO and AQI response depending on wind direction and boundary-layer conditions.",
    metrics: ["Lag check", "Wind alignment", "Downwind warning"],
  },
];

export function Biomass() {
  const [active, setActive] = useState(1);
  const state = BURN_STATES[active];
  return (
    <Section id="biomass" index="04" eyebrow="The Cause"
      title="When the fields burn, the air answers."
      lede="Through the post-monsoon stubble season, fire counts rise over Punjab and Haryana. VAYU treats that as evidence to test, not a conclusion to assume.">
      <div className="mt-8 flex flex-wrap gap-2">
        {BURN_STATES.map((s, i) => (
          <button key={s.label} onClick={() => setActive(i)}
            className="data rounded-full px-4 py-2 text-[12px] transition-colors"
            style={{
              border: "1px solid " + (i === active ? "var(--color-signal)" : "rgba(255,255,255,0.14)"),
              color: i === active ? "var(--color-signal)" : "var(--color-text-2)",
            }}>
            {s.label}
          </button>
        ))}
      </div>
      <p className="mt-5 max-w-[760px] text-[15px] leading-7" style={{ color: "var(--color-text-2)" }}>
        {state.text}
      </p>
      <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <div className="eyebrow mb-3">FIRE ACTIVITY · VIIRS</div>
          <IndiaField mode="hotspots" height={420} />
        </div>
        <div>
          <div className="eyebrow mb-3">HCHO COLUMN · TROPOMI</div>
          <IndiaField mode="aqi" height={420} season={state.season} />
        </div>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-px overflow-hidden rounded-sm border sm:grid-cols-3"
        style={{ borderColor: "var(--line)", background: "var(--line)" }}>
        {state.metrics.map((m) => (
          <div key={m} className="bg-[var(--color-ink-800)] p-4 data text-[12px]" style={{ color: "var(--color-text-2)" }}>
            {m}
          </div>
        ))}
      </div>
      <div className="hairline data mt-6 border-t pt-4 text-[13px]" style={{ color: "var(--color-text-2)" }}>
        Fire signal -&gt; HCHO response -&gt; AQI deterioration -&gt; downwind warning
      </div>
    </Section>
  );
}

/* ====================================================== 10 · ATMOSPHERIC TRANSPORT */
export function Transport() {
  const steps = [
    ["01", "Source window", "Find upwind fires, industrial signals or urban VOC pressure."],
    ["02", "Wind alignment", "Check whether reanalysis winds plausibly carry the plume."],
    ["03", "Receptor impact", "Compare downwind HCHO and AQI response with CPCB context."],
  ];
  return (
    <Section id="transport" index="04" eyebrow="The Movement"
      title="The air carries it.">
      <p className="lede mt-6 max-w-[660px] text-[clamp(1.05rem,1.6vw,1.35rem)]" data-reveal>
        Pollution does not stay where it is made. The orange path is a 48-hour transport
        hypothesis from Delhi; red points are fire pixels. Together they form an evidence
        chain, not a standalone proof.
      </p>
      <div className="mt-8 grid grid-cols-1 gap-px overflow-hidden rounded-sm border md:grid-cols-3"
        style={{ borderColor: "var(--line)", background: "var(--line)" }}>
        {steps.map(([num, label, text]) => (
          <div key={label} className="bg-[var(--color-ink-800)] p-5">
            <div className="data text-[11px]" style={{ color: "var(--color-signal)" }}>{num}</div>
            <h3 className="serif mt-3 text-2xl">{label}</h3>
            <p className="mt-2 text-[14px] leading-6" style={{ color: "var(--color-text-2)" }}>{text}</p>
          </div>
        ))}
      </div>
      <div className="mt-10" role="img"
        aria-label="Atmospheric-transport map: a 48-hour back-trajectory path from Delhi over fire pixels and a seasonal HCHO basemap.">
        <DeckMap mode="transport" height={600} />
      </div>
    </Section>
  );
}

/* ====================================================== 13 · POLICY ACTION BOARD */
const ACTIONS = [
  ["Crop Residue Burning", "High", ["HCHO anomaly", "VIIRS/MODIS fire cluster", "downwind path"], "Increase crop residue burning surveillance and issue downwind VOC precursor alerts."],
  ["Urban-Industrial VOC", "Medium", ["HCHO + NO2 / CO context", "built-up region", "repeated hotspot"], "Prioritize VOC and NO2 source inspection around urban-industrial corridors."],
  ["Port / Shipping Corridor", "Medium", ["coastal HCHO/CO signal", "port proximity", "persistent anomaly"], "Monitor port emissions and shipping-linked combustion signals."],
  ["Biogenic VOC / Ozone Watch", "Medium", ["high vegetation signal", "high temperature", "HCHO enhancement"], "Flag ozone precursor risk during hot and stagnant conditions."],
  ["Transported Plume", "High", ["upwind source", "wind alignment", "downwind hotspot"], "Warn receptor districts and cross-check with CPCB station trends."],
];

function ConfidenceBadge({ level }: { level: string }) {
  const cls = level === "High" ? "confidence-high" : level === "Medium" ? "confidence-medium" : "confidence-low";
  return <span className={`status-badge ${cls}`}>{level} confidence</span>;
}

export function PolicyActionBoard() {
  return (
    <Section id="policy-action" index="06" eyebrow="Decision Layer" variant="paper" grid
      title="From hotspot to action."
      lede="Every detected hotspot should end with a monitoring priority, not just a map point. VAYU turns evidence into a cautious source-attribution hypothesis and a suggested next check.">
      <div className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-sm border lg:grid-cols-5"
        style={{ borderColor: "rgba(0,0,0,0.12)", background: "rgba(0,0,0,0.12)" }}>
        {ACTIONS.map(([title, confidence, evidence, action]) => (
          <div key={title as string} data-reveal className="panel-paper p-6">
            <ConfidenceBadge level={confidence as string} />
            <h3 className="serif mt-5 text-2xl leading-tight">{title as string}</h3>
            <ul className="mt-5 space-y-2">
              {(evidence as string[]).map((e) => (
                <li key={e} className="data text-[11px]" style={{ color: "#8a857a" }}>+ {e}</li>
              ))}
            </ul>
            <p className="mt-5 text-[14px] leading-6" style={{ color: "#4a525b" }}>{action as string}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ====================================================== 14 · EVIDENCE + TRANSPARENT SCORING */
const EVIDENCE_CARDS = [
  ["Sparse monitoring gap", "High", "Ground stations provide accurate surface measurements, but many Indian regions remain spatially under-monitored.", "Satellite layers help fill spatial gaps but require ground validation."],
  ["HCHO as VOC / ozone precursor indicator", "High", "HCHO is a useful proxy for VOC activity and ozone precursor chemistry.", "HCHO columns indicate atmospheric VOC oxidation signals, not direct VOC emissions alone."],
  ["Biomass burning influence", "Medium", "Crop residue burning and forest fires can elevate aerosols, CO, VOCs and HCHO over downwind regions.", "Fire count, wind fields and lag analysis strengthen attribution but do not prove causality by themselves."],
  ["Pollutant-first AQI modeling", "High", "Predicting individual pollutants before calculating AQI improves interpretability and validation.", "The final AQI is only as reliable as the pollutant estimates and station validation."],
];

const FORMULAS = [
  ["CPCB AQI", "AQI = max(pollutant sub-indices)", "The dominant pollutant controls the official AQI category."],
  ["PHV HCHO Anomaly", "PHV = ((HCHO_pixel - HCHO_neighborhood_mean) / HCHO_neighborhood_mean) x 100", "A hotspot is meaningful when it is high relative to nearby background, not only high in absolute value."],
  ["Source Confidence", "Confidence = satellite QA + persistence + fire evidence + wind alignment + CPCB proximity", "Every hotspot receives an evidence-backed confidence label."],
];

export function Evidence() {
  const [weights, setWeights] = useState({ anomaly: 70, fire: 55, wind: 70, persistence: 60 });
  const score = Math.round((weights.anomaly + weights.fire + weights.wind + weights.persistence) / 4);
  const level = score >= 70 ? "High" : score >= 45 ? "Medium" : "Low";
  const controls: [keyof typeof weights, string][] = [
    ["anomaly", "HCHO anomaly"], ["fire", "Fire evidence"], ["wind", "Wind alignment"], ["persistence", "Persistence"],
  ];

  return (
    <Section id="evidence" index="06" eyebrow="Evidence & Scoring" variant="paper" grid
      title="Transparent scoring. No hidden magic."
      lede="VAYU separates official AQI, HCHO anomaly strength and source confidence so the system remains explainable and honest about uncertainty.">
      <div className="mt-12 grid grid-cols-1 gap-8 lg:grid-cols-[1fr_0.9fr]">
        <div className="grid gap-px overflow-hidden rounded-sm border sm:grid-cols-2"
          style={{ borderColor: "rgba(0,0,0,0.12)", background: "rgba(0,0,0,0.12)" }}>
          {EVIDENCE_CARDS.map(([title, confidence, claim, note]) => (
            <div key={title} data-reveal className="evidence-card panel-paper">
              <ConfidenceBadge level={confidence} />
              <h3 className="serif mt-5 text-2xl leading-tight">{title}</h3>
              <p className="mt-4 text-[15px] leading-7" style={{ color: "#303840" }}>{claim}</p>
              <p className="data mt-5 border-t pt-4 text-[11px] leading-5" style={{ borderColor: "rgba(0,0,0,0.12)", color: "#8a857a" }}>
                Trust note: {note}
              </p>
            </div>
          ))}
        </div>
        <div className="grid gap-4">
          {FORMULAS.map(([label, formula, note]) => (
            <div key={label} className="rounded-sm border p-5" style={{ borderColor: "rgba(0,0,0,0.12)", background: "rgba(255,255,255,0.38)" }}>
              <div className="eyebrow">{label}</div>
              <code className="mt-4 block whitespace-pre-wrap rounded-sm p-4 data text-[12px]"
                style={{ background: "#14181d", color: "#ecece6" }}>{formula}</code>
              <p className="mt-3 text-[13px] leading-6" style={{ color: "#4a525b" }}>{note}</p>
            </div>
          ))}
          <div className="rounded-sm border p-5" style={{ borderColor: "rgba(0,0,0,0.12)", background: "rgba(255,255,255,0.38)" }}>
            <div className="flex items-center justify-between gap-4">
              <div className="eyebrow">Demo Confidence</div>
              <ConfidenceBadge level={level} />
            </div>
            <div className="mt-4 space-y-4">
              {controls.map(([key, label]) => (
                <label key={key} className="block data text-[11px]" style={{ color: "#4a525b" }}>
                  <span className="flex justify-between"><span>{label}</span><span>{weights[key]}%</span></span>
                  <input type="range" min={0} max={100} value={weights[key]}
                    onChange={(e) => setWeights((w) => ({ ...w, [key]: Number(e.target.value) }))}
                    className="mt-2 h-1 w-full cursor-pointer appearance-none rounded-full"
                    style={{ background: "linear-gradient(90deg, var(--color-signal-dim), var(--color-signal))" }} />
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}

/* ====================================================== 11 · MODEL ARCHITECTURE */
export function Model() {
  const ref = useDrawOnEnter<HTMLDivElement>(".draw");
  const stages = [
    { x: 90, label: "Satellite", sub: "AOD + gases + met" },
    { x: 290, label: "Features", sub: "collocate + engineer" },
    { x: 490, label: "Random Forest", sub: "per-pollutant (deployed)" },
    { x: 690, label: "AQI", sub: "surface prediction" },
  ];
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return;
    const a = animate(".model-sig", {
      offsetDistance: ["0%", "100%"], duration: 2600, loop: true, ease: "linear",
    });
    return () => {
      a.cancel();
    };
  }, []);
  return (
    <Section id="model" index="05" eyebrow="The Engine" variant="paper"
      title="How the model reads the sky."
      lede="The operational predictor is a per-pollutant Random Forest (optionally a regression-kriging hybrid). It learns surface concentrations directly from the daily satellite + meteorology stack and feeds the AQI maps.">
      <div ref={ref} className="mt-12">
        <svg viewBox="0 0 800 150" className="w-full"
          role="img" aria-label="Deployed model flow: satellite stack, to engineered features, to a per-pollutant Random Forest, to surface AQI.">
          {stages.slice(0, -1).map((s, i) => (
            <path key={i} className="draw" d={`M ${s.x + 60} 60 L ${stages[i + 1].x - 60} 60`}
              stroke="var(--color-signal-dim)" strokeWidth="1.4" fill="none" markerEnd="url(#m)" />
          ))}
          <circle className="model-sig" r="3.5" fill="var(--color-signal)"
            style={{ offsetPath: `path('M 150 60 L 690 60')`, offsetDistance: "0%" } as React.CSSProperties} />
          {stages.map((s) => (
            <g key={s.label}>
              <rect x={s.x - 60} y="35" width="120" height="50" rx="5" fill="var(--color-paper)" stroke="var(--color-signal-dim)" strokeWidth="1.2" />
              <text x={s.x} y="58" textAnchor="middle" className="data" fontSize="14" fill="var(--color-paper-ink)">{s.label}</text>
              <text x={s.x} y="74" textAnchor="middle" className="data" fontSize="10" fill="#8a857a">{s.sub}</text>
            </g>
          ))}
          <defs><marker id="m" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 z" fill="var(--color-signal-dim)" /></marker></defs>
        </svg>
      </div>
      <p className="data mt-6 text-[12px] leading-6" style={{ color: "#8a857a" }}>
        Research / validated, not deployed: a CNN-LSTM (CNN for spatial structure, LSTM for temporal memory)
        is implemented and validated, but is not yet on the live map-generation path. The maps above are the
        Random Forest&apos;s predictions.
      </p>
    </Section>
  );
}

/* ====================================================== 12 · RESULTS */
export function Results() {
  return (
    <Section id="results" index="05" eyebrow="Validation" variant="paper"
      title="Validated against the ground."
      lede="Predicted surface concentrations are checked against real CPCB stations two ways: random cross-validation (held-out days at known stations) and spatial cross-validation (held-out regions).">
      <div className="mt-12 grid grid-cols-2 gap-8 md:grid-cols-4">
        {[
          { l: "R² (PM2.5) · random CV", to: 0.53, d: 2, s: "" },
          { l: "R² (NO₂) · random CV", to: 0.71, d: 2, s: "" },
          { l: "R² (O₃) · random CV", to: 0.66, d: 2, s: "" },
          { l: "CPCB stations", to: 161, d: 0, s: "" },
        ].map((m) => (
          <div key={m.l} data-reveal>
            <div className="serif text-[clamp(2rem,4vw,3rem)]"><CountUp to={m.to} decimals={m.d} suffix={m.s} /></div>
            <div className="data mt-1 text-[11px]" style={{ color: "#8a857a" }}>{m.l}</div>
          </div>
        ))}
      </div>
      <p className="data mt-8 text-[12px]" style={{ color: "#8a857a" }}>
        NO₂, O₃ and CO meet or beat India benchmarks under random CV; PM and SO₂ are solid. Spatial
        extrapolation to unmonitored regions stays hard (spatial-CV R² 0.02–0.19) — the honest gap
        between random and spatial CV shows exactly that.
      </p>
    </Section>
  );
}

/* ====================================================== 13 · RESEARCH INSIGHTS */
const INSIGHTS = [
  ["The Indo-Gangetic Plain is a persistent reactive corridor.", "Highest sustained AQI & HCHO, year on year."],
  ["Stubble burning prints onto the air within days.", "Oct–Nov fire peaks track HCHO and PM2.5 surges."],
  ["Hotspots are stable, not random.", "PHV / Gi* / DBSCAN agree across 2019–2022."],
  ["Transport links source and city.", "Punjab fires reach Delhi's boundary layer in 36–48 h."],
];
export function Insights() {
  return (
    <Section id="insights" index="05" eyebrow="The Discoveries" variant="paper"
      title="What the data revealed.">
      <div className="mt-10">
        {INSIGHTS.map(([big, small], i) => (
          <div key={i} data-reveal className="border-t py-8" style={{ borderColor: "rgba(0,0,0,0.12)" }}>
            <h3 className="serif text-[clamp(1.6rem,3.4vw,2.6rem)] leading-tight">{big}</h3>
            <p className="data mt-2 text-[13px]" style={{ color: "#8a857a" }}>{small}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ====================================================== 14 · FUTURE APPLICATIONS */
const APPS = [
  ["NCAP", "Track non-attainment cities toward national targets"],
  ["Urban Planning", "Site infrastructure away from chronic exposure"],
  ["Public Health", "Quantify exposure where no monitor exists"],
  ["Climate Monitoring", "Link air quality to emissions & climate"],
  ["ISRO Applications", "Operationalise INSAT-derived air quality"],
  ["Smart Cities", "Daily, hyperlocal air-quality intelligence"],
];
export function Future() {
  return (
    <Section id="applications" index="06" eyebrow="The Reach" variant="paper"
      title="From orbit to policy.">
      <div className="mt-12 grid grid-cols-1 gap-px sm:grid-cols-2 md:grid-cols-3"
        style={{ background: "rgba(0,0,0,0.12)" }}>
        {APPS.map(([t, d]) => (
          <div key={t} data-reveal className="panel-paper p-7">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-signal-dim)" strokeWidth="1.5">
              <circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3v18" />
            </svg>
            <h3 className="serif mt-4 text-xl">{t}</h3>
            <p className="mt-1 text-[14px]" style={{ color: "#4a525b" }}>{d}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ====================================================== 15 · FINAL IMPACT */
export function FinalImpact() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const spans = el.querySelectorAll<HTMLElement>(".reveal-line > span");
    if (reduce) { spans.forEach((s) => (s.style.transform = "none")); return; }
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (!e.isIntersecting) return; io.disconnect();
      animate(spans, { translateY: ["110%", "0%"], duration: 1400, delay: 120, ease: RESOLVE
 });
    }), { threshold: 0.4 });
    io.observe(el); return () => io.disconnect();
  }, []);
  return (
    <section id="impact" className="relative flex min-h-screen items-center justify-center overflow-hidden">
      <div className="absolute inset-0 opacity-60"><IndiaField mode="final" height={900} className="h-full" /></div>
      <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at center, transparent 30%, var(--color-ink-900) 80%)" }} />
      <div ref={ref} className="relative z-10 px-6 text-center">
        <h2 className="display text-[clamp(2.2rem,6vw,5rem)]">
          <span className="reveal-line"><span>We cannot improve</span></span>
          <span className="reveal-line"><span>what we cannot see.</span></span>
        </h2>
      </div>
    </section>
  );
}

/* ====================================================== 16/17 · FOOTER */
export function Footer() {
  const cols = [
    ["Data Sources", ["INSAT-3D AOD (MOSDAC)", "Sentinel-5P TROPOMI", "CPCB CAAQMS", "ERA5 / IMDAA", "MODIS / VIIRS fire"]],
    ["Prototype Status", ["Interactive sample geospatial layers", "Real-data pipeline ready", "Decision-support, not measurement replacement", "Validation-first roadmap"]],
    ["Jump To", ["Methodology", "Evidence", "AQI Map", "Policy Actions"]],
  ];
  return (
    <footer id="footer" className="relative border-t hairline">
      <div className="mx-auto max-w-[1280px] px-6 py-20 md:px-16">
        <div className="serif text-3xl">VAYU — India&apos;s Air, Observed</div>
        <p className="mt-4 max-w-[760px] text-[15px] leading-7" style={{ color: "var(--color-text-2)" }}>
          Built for Bharatiya Antariksh Hackathon 2026 · Challenge 03. Interactive prototype using sample
          geospatial layers, designed for Sentinel-5P, INSAT-3D, CPCB, ERA5/IMDAA and MODIS/VIIRS integration.
        </p>
        <div className="mt-12 grid grid-cols-1 gap-10 md:grid-cols-3">
          {cols.map(([h, items]) => (
            <div key={h as string}>
              <div className="eyebrow mb-4">{h as string}</div>
              <ul className="space-y-2">
                {(items as string[]).map((it) => {
                  const href: Record<string, string> = {
                    Methodology: "#pipeline", Evidence: "#evidence", "AQI Map": "#aqi", "Policy Actions": "#policy-action",
                  };
                  return (
                    <li key={it} className="data text-[13px]" style={{ color: "var(--color-text-2)" }}>
                      {href[it] ? <a href={href[it]}>{it}</a> : it}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
        <div className="hairline mt-16 flex flex-wrap items-center justify-between gap-4 border-t pt-6 data text-[11px]" style={{ color: "var(--color-text-3)" }}>
          <a href="https://github.com/aksh08022006/vayu-aqi-hcho" target="_blank" rel="noreferrer">github.com/aksh08022006/vayu-aqi-hcho</a>
          <span>Team: VAYU · sample-data preview build</span>
        </div>
      </div>
    </footer>
  );
}
