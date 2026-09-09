"use client";
import { useEffect, useState } from "react";

type DataStatus = "synthetic_demo" | "real_validated" | "real_observational" | string;

interface Metadata {
  data_status: DataStatus;
  date: string;
  zone?: { method: string; selected_k: number; n_cells: number; zone_labels: string[] };
  isolation_forest?: { method: string; contamination: number; n_anomalies: number; n_cells: number };
  scientific_note?: string;
}

export type LayerKind = "aqi" | "gas" | "zones" | "isolation" | "transport" | "hotspots";

const STATUS_LABEL: Record<DataStatus, string> = {
  synthetic_demo: "Synthetic demo",
  real_validated: "Real · validated",
  real_observational: "Real · observational",
};

const STATUS_COLOR: Record<DataStatus, string> = {
  synthetic_demo: "#e0cd66",
  real_validated: "#6cb470",
  real_observational: "#7ab8e0",
};

const LAYER_OUTPUT: Record<LayerKind, string> = {
  aqi: "Official AQI · RF model output",
  gas: "Satellite column · normalised",
  zones: "Exploratory · K-Means relative clusters",
  isolation: "Anomaly baseline · unsupervised",
  transport: "Transport hypothesis · ERA5 winds",
  hotspots: "PHV anomaly attribution · exploratory",
};

const LAYER_SOURCE: Record<LayerKind, string> = {
  aqi: "TROPOMI + MODIS → RF predictor",
  gas: "Sentinel-5P TROPOMI OFFL L3",
  zones: "Gridded AQI/HCHO/NO₂/CO stack",
  isolation: "HCHO / NO₂ / CO / FRP feature vector",
  transport: "ERA5 reanalysis · MODIS FIRMS",
  hotspots: "TROPOMI HCHO · PHV / Gi*",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}

export function ProvenancePanel({ mode }: { mode: LayerKind }) {
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    fetch("/data/analysis_metadata.json")
      .then((r) => r.json())
      .then(setMeta)
      .catch(() => null);
  }, []);

  if (!meta) return null;

  const status = meta.data_status;
  const statusLabel = STATUS_LABEL[status] ?? status;
  const dotColor = STATUS_COLOR[status] ?? "#a7aeb6";

  const box: React.CSSProperties = {
    position: "absolute", left: 12, top: 12, zIndex: 11,
    fontFamily: "var(--font-mono)",
  };

  const pill: React.CSSProperties = {
    display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer",
    background: "rgba(14,18,23,0.92)", border: "1px solid rgba(255,255,255,0.14)",
    borderRadius: 4, padding: "5px 10px", fontSize: 11, color: "#ECECE6",
    userSelect: "none",
  };

  const card: React.CSSProperties = {
    marginTop: 6,
    background: "rgba(14,18,23,0.96)", border: "1px solid rgba(255,255,255,0.14)",
    borderRadius: 4, padding: "12px 14px", width: 260,
    boxShadow: "0 18px 50px rgba(0,0,0,0.35)",
  };

  const row = (label: string, value: React.ReactNode) => (
    <div key={label} style={{ display: "grid", gridTemplateColumns: "90px 1fr", gap: 6, marginBottom: 6 }}>
      <span style={{ color: "#6b7480", fontSize: 10, letterSpacing: "0.1em", paddingTop: 1 }}>{label.toUpperCase()}</span>
      <span style={{ color: "#c8cccf", fontSize: 11, lineHeight: "16px" }}>{value}</span>
    </div>
  );

  return (
    <div style={box}>
      {/* collapsed pill — always visible */}
      <button
        style={pill}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label="Toggle data provenance panel"
      >
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: dotColor, flexShrink: 0 }} />
        {statusLabel}
        <span style={{ color: "#6b7480", marginLeft: 2 }}>{open ? "▲" : "▼"}</span>
      </button>

      {/* expanded card */}
      {open && (
        <div style={card} role="complementary" aria-label="Layer provenance details">
          <div style={{ fontSize: 10, letterSpacing: "0.13em", color: "#6b7480", marginBottom: 10 }}>
            DATA PROVENANCE
          </div>
          {row("Status", <span style={{ color: dotColor }}>{statusLabel}</span>)}
          {row("Date", formatDate(meta.date))}
          {row("Source", LAYER_SOURCE[mode])}
          {row("Output type", LAYER_OUTPUT[mode])}
          {mode === "aqi" && row("Validation", "RF R² 0.53–0.71 · 161 CPCB stations")}
          {mode === "zones" && meta.zone && row("Clusters", `K=${meta.zone.selected_k} · ${meta.zone.n_cells} cells`)}
          {mode === "isolation" && meta.isolation_forest &&
            row("Anomalies", `${meta.isolation_forest.n_anomalies} / ${meta.isolation_forest.n_cells} cells (contamination ${meta.isolation_forest.contamination})`)}
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.1)", marginTop: 8, paddingTop: 8, fontSize: 10, color: "#6b7480", lineHeight: "15px" }}>
            {status === "synthetic_demo"
              ? "⚠ Synthetic data — reproducible but not real observations. Suitable for prototype demonstration only."
              : meta.scientific_note ?? ""}
          </div>
          <button
            onClick={() => setOpen(false)}
            style={{ marginTop: 8, fontSize: 10, color: "#6b7480", cursor: "pointer", background: "none", border: "none", padding: 0 }}
          >
            Close ✕
          </button>
        </div>
      )}
    </div>
  );
}
