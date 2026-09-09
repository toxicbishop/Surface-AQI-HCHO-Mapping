"use client";
import { useState, useCallback } from "react";

export type CellInfo = {
  lon: number;
  lat: number;
  aqi?: number;
  aqiBand?: string;
  hcho?: number;
  zoneLabel?: string;
  zoneId?: number;
  isolationScore?: number;
  nearbyFireCount?: number;
  nearbyFRP?: number;
  source?: string;
  dataStatus?: string;
};

const AQI_BANDS = [
  { max: 50, label: "Good", color: "#6cb470" },
  { max: 100, label: "Satisfactory", color: "#b5cc52" },
  { max: 200, label: "Moderate", color: "#e0cd66" },
  { max: 300, label: "Poor", color: "#ee9a4e" },
  { max: 400, label: "Very Poor", color: "#d65246" },
  { max: Infinity, label: "Severe", color: "#874b9b" },
];

function aqiBand(v?: number): { label: string; color: string } {
  if (!v && v !== 0) return { label: "—", color: "#6b7480" };
  return AQI_BANDS.find((b) => v <= b.max) ?? AQI_BANDS[AQI_BANDS.length - 1];
}

function Row({ label, value, color }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "110px 1fr", gap: 6, marginBottom: 5 }}>
      <span style={{ color: "#6b7480", fontSize: 10, letterSpacing: "0.1em", paddingTop: 1 }}>
        {label.toUpperCase()}
      </span>
      <span style={{ color: color ?? "#c8cccf", fontSize: 11, lineHeight: "16px" }}>{value}</span>
    </div>
  );
}

interface Props {
  cell: CellInfo | null;
  onClose: () => void;
}

export function LocationExplorer({ cell, onClose }: Props) {
  if (!cell) return null;

  const { label: aqiLabel, color: aqiColor } = aqiBand(cell.aqi);

  const panelStyle: React.CSSProperties = {
    position: "absolute", right: 0, top: 0, bottom: 0, zIndex: 20,
    width: "min(300px, 90vw)",
    background: "rgba(10,13,18,0.97)",
    borderLeft: "1px solid rgba(255,255,255,0.13)",
    fontFamily: "var(--font-mono)",
    display: "flex", flexDirection: "column",
    overflow: "auto",
    boxShadow: "-18px 0 60px rgba(0,0,0,0.45)",
    animation: "slideInRight 0.2s ease-out",
  };

  return (
    <>
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
      `}</style>
      <aside style={panelStyle} aria-label="Location data explorer">
        {/* header */}
        <div style={{ padding: "14px 14px 10px", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 10, letterSpacing: "0.14em", color: "#6b7480" }}>
              LOCATION EXPLORER
            </span>
            <button
              onClick={onClose}
              style={{ color: "#6b7480", fontSize: 16, cursor: "pointer", background: "none", border: "none", padding: "0 2px", lineHeight: 1 }}
              aria-label="Close location explorer"
            >
              ✕
            </button>
          </div>
          <div style={{ marginTop: 6, fontSize: 13, color: "#ECECE6" }}>
            {cell.lon.toFixed(2)}°E · {cell.lat.toFixed(2)}°N
          </div>
        </div>

        {/* body */}
        <div style={{ padding: "14px", flex: 1 }}>
          {/* AQI */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 10, letterSpacing: "0.13em", color: "#6b7480", marginBottom: 6 }}>AQI</div>
            {cell.aqi != null ? (
              <>
                <div style={{ fontSize: 28, fontWeight: 600, color: aqiColor, lineHeight: 1 }}>
                  {Math.round(cell.aqi)}
                </div>
                <div style={{ fontSize: 11, color: aqiColor, marginTop: 3 }}>{aqiLabel}</div>
              </>
            ) : (
              <div style={{ fontSize: 13, color: "#6b7480" }}>Not available</div>
            )}
          </div>

          <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 12 }}>
            <Row
              label="HCHO column"
              value={cell.hcho != null ? `${(cell.hcho * 100).toFixed(1)}% (norm.)` : "—"}
            />
            {cell.zoneLabel && (
              <Row
                label="K-Means zone"
                value={`Zone ${(cell.zoneId ?? 0) + 1} · ${cell.zoneLabel}`}
              />
            )}
            {cell.isolationScore != null && (
              <Row
                label="IF anomaly score"
                value={cell.isolationScore.toFixed(4)}
                color={cell.isolationScore > 0 ? "#ff7a45" : "#c8cccf"}
              />
            )}
            {cell.nearbyFireCount != null && cell.nearbyFireCount > 0 && (
              <Row
                label="Nearby fires"
                value={`${cell.nearbyFireCount} pixel${cell.nearbyFireCount !== 1 ? "s" : ""} · FRP ${cell.nearbyFRP?.toFixed(0) ?? 0} MW`}
              />
            )}
            {cell.source && (
              <Row
                label="Attribution"
                value={cell.source.replace(/_/g, " ")}
              />
            )}
          </div>

          {/* data-status footer */}
          <div style={{
            marginTop: 14, padding: "8px 10px",
            borderRadius: 4, border: "1px solid rgba(224,205,102,0.3)",
            background: "rgba(224,205,102,0.06)",
            fontSize: 10, color: "#b89c3a", lineHeight: "15px",
          }}>
            {cell.dataStatus === "synthetic_demo"
              ? "⚠ Synthetic demo data — not real observations."
              : "✓ Real observational layer."}
          </div>
        </div>

        <div style={{ padding: "10px 14px", borderTop: "1px solid rgba(255,255,255,0.08)", fontSize: 10, color: "#4a525b" }}>
          Click any map cell to inspect · hover for quick readout
        </div>
      </aside>
    </>
  );
}

/** Hook to manage selected cell state — import alongside LocationExplorer */
export function useCellSelect() {
  const [cell, setCell] = useState<CellInfo | null>(null);
  const onCellSelect = useCallback((c: CellInfo) => setCell(c), []);
  const onCellClose  = useCallback(() => setCell(null), []);
  return { cell, onCellSelect, onCellClose };
}
