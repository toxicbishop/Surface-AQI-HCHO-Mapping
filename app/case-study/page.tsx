"use client";
import { useState } from "react";
import { Section } from "@/components/Section";
import { DeckMap } from "@/components/DeckMap";
import { LocationExplorer, useCellSelect } from "@/components/LocationExplorer";
import { CellSelectContext } from "@/lib/CellSelectContext";
import { ChapterPager } from "@/components/ChapterNav";

/* ─── Attribution caveat ──────────────────────────────────────────────────── */
function AttributionCaveat() {
  return (
    <div
      style={{
        background: "rgba(224,205,102,0.07)",
        border: "1px solid rgba(224,205,102,0.35)",
        borderRadius: 4,
        padding: "14px 16px",
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        color: "#b89c3a",
        lineHeight: "19px",
        marginTop: 16,
      }}
      role="note"
      aria-label="Scientific attribution caveat"
    >
      <span style={{ fontWeight: 600 }}>Attribution caveat · </span>
      Fire → HCHO correlation is evidence for investigation, not proof of causality. A
      confirmed attribution requires dispersion modelling, meteorological alignment, and
      validated ground-level measurements. The back-trajectory and HCHO anomaly maps below are
      exploratory indicators only.
    </div>
  );
}

/* ─── Timeline step cards ─────────────────────────────────────────────────── */
const TIMELINE = [
  {
    num: "01",
    label: "The harvest window opens",
    text: "Post-monsoon, October 2021. Kharif harvest finishes in Punjab and Haryana. Farmers have 2–4 weeks before the next rabi crop must be sown. The cheapest way to clear residue is fire.",
    signal: "MODIS FIRMS fire pixel count rising",
  },
  {
    num: "02",
    label: "Fire pixels cluster over the agricultural belt",
    text: "VIIRS and MODIS detect active fire clusters across the Majha, Malwa and Doaba districts of Punjab and Haryana. FRP values exceed 100 MW at peak — high confidence biomass-burning signals.",
    signal: "FRP > 100 MW · High attribution confidence",
  },
  {
    num: "03",
    label: "HCHO column rises downwind",
    text: "TROPOMI HCHO column shows elevated readings south-east of the fire belt — consistent with VOC oxidation products carried by prevailing north-westerly winds. The VAYU PHV detector flags 91 clusters.",
    signal: "TROPOMI HCHO anomaly · PHV flagged",
  },
  {
    num: "04",
    label: "ERA5 winds align with the trajectory",
    text: "The 48-hour back-trajectory from Delhi traces back north-west along the Gangetic Plain towards the fire belt. The wind alignment makes fire-linked transport a plausible hypothesis.",
    signal: "ERA5 reanalysis · back-trajectory path",
  },
  {
    num: "05",
    label: "AQI deteriorates in Delhi NCR",
    text: "The RF-predicted AQI for Delhi NCR rises toward the Very Poor–Severe boundary. PM2.5 is the dominant sub-index. Transport from the fire belt is one candidate contributor, alongside local traffic and industrial sources.",
    signal: "RF AQI model · CPCB validated (R² 0.53–0.71)",
  },
];

/* ─── Main narrative section ──────────────────────────────────────────────── */
function NarrativeTimeline() {
  const [active, setActive] = useState(0);
  return (
    <Section
      id="case-study-timeline"
      index="CS"
      eyebrow="The Evidence Chain"
      title="From burning field to city air."
      lede="Five signals, one causal hypothesis. Each step is a piece of corroborating evidence — not a standalone proof."
    >
      <AttributionCaveat />
      <div className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-sm border md:grid-cols-5"
        style={{ borderColor: "var(--line)", background: "var(--line)" }}>
        {TIMELINE.map((s, i) => (
          <button
            key={s.num}
            onClick={() => setActive(i)}
            aria-pressed={active === i}
            className="text-left"
            style={{
              background: active === i ? "rgba(255,122,69,0.08)" : "var(--bg)",
              padding: "20px 16px",
              borderBottom: active === i ? "2px solid var(--color-signal)" : "2px solid transparent",
              transition: "background 0.2s",
            }}
          >
            <div style={{ fontSize: 11, color: "var(--color-signal)", fontFamily: "var(--font-mono)" }}>{s.num}</div>
            <div className="serif mt-2 text-[15px] leading-tight">{s.label}</div>
          </button>
        ))}
      </div>
      <div className="mt-6 rounded-sm border p-6" style={{ borderColor: "var(--line)" }}>
        <p className="text-[15px] leading-7" style={{ color: "var(--color-text-2)" }}>
          {TIMELINE[active].text}
        </p>
        <div className="mt-4 data text-[11px]" style={{ color: "var(--color-text-3)" }}>
          Signal: {TIMELINE[active].signal}
        </div>
      </div>
    </Section>
  );
}

/* ─── Fire + transport map ────────────────────────────────────────────────── */
function FireAndTransport() {
  return (
    <Section
      id="case-study-transport"
      index="CS"
      eyebrow="Fire + Wind"
      title="48-hour transport hypothesis."
      lede="Orange path: ERA5 back-trajectory from Delhi. Red dots: MODIS active fire pixels. HCHO basemap: TROPOMI column intensity."
    >
      <div className="mt-8" role="img" aria-label="Atmospheric transport map showing 48-hour back-trajectory from Delhi over MODIS fire pixels and TROPOMI HCHO basemap.">
        <DeckMap mode="transport" height={580} />
      </div>
      <AttributionCaveat />
    </Section>
  );
}

/* ─── HCHO hotspots map ───────────────────────────────────────────────────── */
function HCHOHotspots() {
  return (
    <Section
      id="case-study-hcho"
      index="CS"
      eyebrow="HCHO Anomalies"
      title="Where the air turns reactive."
      lede="PHV-attributed HCHO hotspots over the TROPOMI seasonal mean. Coloured by source hypothesis. Click any hotspot to inspect."
    >
      <div className="mt-8" role="img" aria-label="Map of PHV HCHO hotspots attributed by source type over the TROPOMI HCHO basemap.">
        <DeckMap mode="hotspots" height={560} />
      </div>
      <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 data text-[12px]" style={{ color: "var(--color-text-2)" }}>
        {([
          ["agri_burning", "#ff7a45"],
          ["urban", "#a78bfa"],
          ["industrial", "#f2a93b"],
          ["biogenic", "#7fbf7f"],
          ["other", "#969ca4"],
        ] as [string, string][]).map(([k, c]) => (
          <span key={k} className="flex items-center gap-2">
            <span className="block h-2.5 w-2.5 rounded-full" style={{ background: c }} />
            {k.replace(/_/g, " ")}
          </span>
        ))}
      </div>
    </Section>
  );
}

/* ─── AQI impact map ──────────────────────────────────────────────────────── */
function AQIImpact() {
  return (
    <Section
      id="case-study-aqi"
      index="CS"
      eyebrow="AQI Impact"
      title="Delhi NCR — air quality during the fire window."
      lede="RF-predicted surface AQI, coloured by CPCB scale. Delhi NCR trends toward Very Poor during peak fire activity. PM2.5 is the dominant sub-index."
    >
      <div className="mt-8" role="img" aria-label="CPCB-scale surface AQI map of India predicted by the Random Forest model during October 2021 fire window.">
        <DeckMap mode="aqi" height={560} />
      </div>
      <div className="mt-4 data text-[12px]" style={{ color: "var(--color-text-3)" }}>
        RF predictor · CPCB validated (random-CV R² 0.53–0.71) · 161 stations · Oct 2021
      </div>
    </Section>

  );
}

/* ─── Policy recommendation ───────────────────────────────────────────────── */
function PolicyRecommendation() {
  const STEPS = [
    { label: "Monitor", text: "Increase CPCB station sampling frequency during fire season in Punjab/Haryana. Enable real-time HCHO anomaly alerts when satellite overpass data becomes available." },
    { label: "Attribute cautiously", text: "Combine fire counts, HCHO anomaly scores, and wind alignment before issuing a source-attribution statement. A single satellite observation is not sufficient." },
    { label: "Warn downwind", text: "When trajectory, HCHO, and AQI trends align, issue advisory for receptor districts including Delhi NCR, Haryana plains, and western UP." },
    { label: "Act on the source", text: "Direct enforcement resources toward fire-prone talukas where FRP is consistently high. Provide farmers with residue management alternatives." },
  ];
  return (
    <Section
      id="case-study-policy"
      index="CS"
      eyebrow="Decision Layer"
      title="From hotspot to action."
      lede="What a monitoring officer would do with this evidence chain."
    >
      <div className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-sm border sm:grid-cols-2"
        style={{ borderColor: "var(--line)", background: "var(--line)" }}>
        {STEPS.map(({ label, text }) => (
          <div key={label} className="p-6" style={{ background: "var(--bg)" }}>
            <div className="data text-[11px]" style={{ color: "var(--color-signal)", letterSpacing: "0.13em" }}>
              {label.toUpperCase()}
            </div>
            <p className="mt-3 text-[14px] leading-6" style={{ color: "var(--color-text-2)" }}>{text}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

/* ─── Page ────────────────────────────────────────────────────────────────── */
export default function CaseStudyPage() {
  const { cell, onCellSelect, onCellClose } = useCellSelect();

  return (
    <CellSelectContext.Provider value={onCellSelect}>
      <main className="relative">
        {/* Sticky location explorer panel */}
        <div className="fixed inset-y-0 right-0 z-50 pointer-events-none">
          <div className="pointer-events-auto h-full">
            <LocationExplorer
              cell={cell ? { ...cell, dataStatus: "synthetic_demo" } : null}
              onClose={onCellClose}
            />
          </div>
        </div>

        {/* Page intro */}
        <Section
          id="case-study-intro"
          index="CS"
          eyebrow="Case Study"
          title="Punjab–Haryana–Delhi: the fire-smoke corridor."
          lede="Post-monsoon stubble burning, October 2021. This page walks through every layer of the VAYU evidence chain — fire activity, HCHO anomalies, wind transport, and AQI impact — and explains what each signal means and what it does not prove."
        >
          <div className="mt-6 inline-flex max-w-full flex-wrap gap-2 rounded-sm border px-3 py-2 data text-[11px]"
            style={{ borderColor: "var(--line)", color: "var(--color-text-2)", background: "rgba(255,255,255,0.03)" }}>
            <span style={{ color: "var(--color-signal)" }}>⚠ Synthetic demo data</span>
            <span>Oct 2021 post-monsoon window</span>
            <span>TROPOMI / MODIS simulated grid</span>
            <span>All layers: exploratory, not operational</span>
          </div>
        </Section>

        <NarrativeTimeline />
        <FireAndTransport />
        <HCHOHotspots />
        <AQIImpact />
        <PolicyRecommendation />
        <ChapterPager current="/case-study" />
      </main>
    </CellSelectContext.Provider>
  );
}
