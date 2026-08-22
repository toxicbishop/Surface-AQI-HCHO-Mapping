"use client";
import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { ScatterplotLayer, PathLayer, PolygonLayer, BitmapLayer } from "@deck.gl/layers";
import { AQI_STOPS } from "@/lib/india";

type Mode = "aqi" | "gas" | "hotspots" | "transport" | "zones" | "isolation";
type RGB = [number, number, number];
type LayerStatus = "loading" | "ready" | "partial" | "error";
type Hotspot = {
  id?: string;
  lon: number;
  lat: number;
  source: string;
  detail?: string;
  frp?: number;
  n?: number;
  _i?: number;
};
type ZoneCell = { lon: number; lat: number; zone_id: number; zone_label: string; aqi?: number; zone_score?: number };
type IsolationCell = { lon: number; lat: number; isolation_score: number; cluster_id: number; cluster_size: number; hcho?: number };

// Real dark basemap (CARTO dark — coastlines, state borders, cities) + a faint
// India outline highlight. CARTO public basemaps need attribution, no API key.
const CARTO = ["a", "b", "c", "d"].map(
  (s) => `https://${s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png`
);
const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    carto: { type: "raster", tiles: CARTO, tileSize: 256, attribution: "© OpenStreetMap, © CARTO" },
    india: { type: "geojson", data: "/data/india.geojson" },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": "#07090c" } },
    { id: "carto", type: "raster", source: "carto", paint: { "raster-opacity": 0.7 } },
    // faint land tint so India reads clearly against the ocean
    { id: "ifill", type: "fill", source: "india", paint: { "fill-color": "#103a1e", "fill-opacity": 0.16 } },
    // crisp official boundary
    { id: "iline", type: "line", source: "india", paint: { "line-color": "#ff7a33", "line-width": 1.4, "line-opacity": 0.6 } },
  ],
};

/* =====================================================================
 * Premium smooth scientific fields.
 * Each pollutant grid is rendered as a value image (one pixel per cell)
 * shown through deck.gl BitmapLayer with GPU bilinear filtering, so cells
 * blend into continuous atmospheric gradients instead of hard squares.
 * A NaN-aware Gaussian pre-smooth adds diffusion; opacity scales with the
 * value (low = transparent, high = visible) and feathers to 0 at edges.
 * ===================================================================== */
type Stop = [number, RGB];
// PM2.5-style AQI ramp (IQAir/Windy feel): blue→green→yellow→orange→red→deep purple
const AQI_FIELD: Stop[] = [
  [0, [122, 170, 210]], [0.1, [122, 170, 210]], [0.2, [120, 190, 120]],
  [0.4, [235, 215, 110]], [0.6, [238, 165, 80]], [0.8, [216, 84, 70]], [1, [135, 75, 155]],
];
// per-gas perceptual ramps (soft, non-neon)
const FIELD_RAMP: Record<string, Stop[]> = {
  aod: [[0, [225, 210, 180]], [0.5, [210, 160, 90]], [1, [120, 75, 45]]],
  no2: [[0, [110, 200, 210]], [0.34, [80, 130, 210]], [0.7, [235, 150, 70]], [1, [210, 70, 60]]],
  so2: [[0, [120, 190, 130]], [0.34, [225, 215, 110]], [0.7, [235, 150, 70]], [1, [150, 45, 45]]],
  co: [[0, [200, 210, 225]], [0.5, [100, 140, 210]], [1, [60, 60, 140]]],
  o3: [[0, [120, 205, 195]], [0.34, [120, 190, 120]], [0.7, [235, 180, 90]], [1, [210, 75, 60]]],
  hcho: [[0, [235, 225, 150]], [0.4, [240, 170, 80]], [0.7, [225, 90, 70]], [1, [140, 70, 150]]],
};
function interpRamp(stops: Stop[], t: number): RGB {
  if (t <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    if (t <= stops[i][0]) {
      const [p0, c0] = stops[i - 1], [p1, c1] = stops[i];
      const k = (t - p0) / (p1 - p0 || 1);
      return [0, 1, 2].map((j) => Math.round(c0[j] + (c1[j] - c0[j]) * k)) as RGB;
    }
  }
  return stops[stops.length - 1][1];
}
function gradFromStops(stops: Stop[]): string {
  return `linear-gradient(90deg, ${stops
    .map(([p, c]) => `rgb(${c[0]},${c[1]},${c[2]}) ${Math.round(p * 100)}%`)
    .join(", ")})`;
}
// NaN-aware Gaussian blur over the regular grid (atmospheric diffusion)
function blurNaN(a: Float32Array, cols: number, rows: number, r: number) {
  if (r <= 0) return;
  const src = Float32Array.from(a), s2 = 2 * 0.9 * 0.9;
  for (let y = 0; y < rows; y++)
    for (let x = 0; x < cols; x++) {
      let sum = 0, w = 0;
      for (let dy = -r; dy <= r; dy++)
        for (let dx = -r; dx <= r; dx++) {
          const xx = x + dx, yy = y + dy;
          if (xx < 0 || xx >= cols || yy < 0 || yy >= rows) continue;
          const v = src[yy * cols + xx];
          if (!Number.isFinite(v)) continue;
          const wt = Math.exp(-(dx * dx + dy * dy) / s2);
          sum += v * wt; w += wt;
        }
      a[y * cols + x] = w > 0 ? sum / w : NaN;
    }
}
type FieldOpts = { lo?: number; hi?: number; aMin?: number; aMax?: number; blur?: number };
// Build a value image (one pixel per grid cell) + lng/lat bounds for BitmapLayer.
function buildField(pts: number[][], stops: Stop[], o: FieldOpts) {
  if (!pts.length || typeof document === "undefined") return null;
  const { lo = 0, hi = 1, aMin = 0.18, aMax = 0.72, blur = 1 } = o;
  const lons = Array.from(new Set(pts.map((p) => p[0]))).sort((a, b) => a - b);
  const lats = Array.from(new Set(pts.map((p) => p[1]))).sort((a, b) => a - b);
  let res = Infinity;
  for (let i = 1; i < lons.length; i++) res = Math.min(res, lons[i] - lons[i - 1]);
  if (!Number.isFinite(res) || res <= 0) res = 0.5;
  const minLon = lons[0], maxLon = lons[lons.length - 1], minLat = lats[0], maxLat = lats[lats.length - 1];
  const cols = Math.round((maxLon - minLon) / res) + 1;
  const rows = Math.round((maxLat - minLat) / res) + 1;
  const val = new Float32Array(cols * rows).fill(NaN);
  for (const p of pts) {
    if (!Number.isFinite(p[2])) continue;
    const x = Math.round((p[0] - minLon) / res), y = Math.round((maxLat - p[1]) / res);
    if (x >= 0 && x < cols && y >= 0 && y < rows) val[y * cols + x] = p[2];
  }
  blurNaN(val, cols, rows, blur);
  const cv = document.createElement("canvas");
  cv.width = cols; cv.height = rows;
  const ctx = cv.getContext("2d");
  if (!ctx) return null;
  const img = ctx.createImageData(cols, rows);
  for (let i = 0; i < cols * rows; i++) {
    const v = val[i];
    if (!Number.isFinite(v)) { img.data[i * 4 + 3] = 0; continue; }
    const t = Math.min(1, Math.max(0, (v - lo) / (hi - lo)));
    const [r, g, b] = interpRamp(stops, t);
    img.data[i * 4] = r; img.data[i * 4 + 1] = g; img.data[i * 4 + 2] = b;
    img.data[i * 4 + 3] = Math.round((aMin + (aMax - aMin) * Math.pow(t, 0.85)) * 255);
  }
  ctx.putImageData(img, 0, 0);
  const half = res / 2;
  return { image: cv, bounds: [minLon - half, minLat - half, maxLon + half, maxLat + half] as [number, number, number, number] };
}
const ZONE_RGB: RGB[] = [
  [108, 180, 112], [224, 205, 102], [238, 154, 78], [214, 82, 70], [135, 75, 155],
];
const SOURCE_RGB: Record<string, RGB> = {
  agri_burning: [255, 122, 69], urban: [167, 139, 250], industrial: [242, 169, 59],
  forest_fire: [255, 90, 60], biogenic: [127, 191, 127], other: [150, 156, 164],
};

const SOURCE_ACTION: Record<string, string> = {
  agri_burning: "Crop residue burning surveillance and downwind VOC precursor alert",
  industrial: "Industrial VOC inspection and stack-emission monitoring",
  urban: "Traffic, NO2 and urban VOC precursor monitoring",
  biogenic: "Ozone precursor watch during high-temperature periods",
  forest_fire: "Forest-fire smoke and VOC plume monitoring",
  other: "Ground validation required before attribution",
};

function confidenceFor(h: Hotspot): "High" | "Medium" | "Low" {
  const frp = h.frp ?? 0;
  if (h.source === "agri_burning" && frp > 100) return "High";
  if (frp > 0 || h.source !== "other") return "Medium";
  return "Low";
}

function confidenceClass(level: string) {
  return level === "High" ? "confidence-high" : level === "Medium" ? "confidence-medium" : "confidence-low";
}

function sourceLabel(source: string) {
  return source.replace(/_/g, " ");
}

const GAS_LABEL: Record<string, string> = {
  aod: "AOD", no2: "NO₂", so2: "SO₂", co: "CO", o3: "O₃", hcho: "HCHO",
};

function MapLegend({ mode, gas }: { mode: Mode; gas: string }) {
  const box: React.CSSProperties = {
    position: "absolute", left: 12, bottom: 12, zIndex: 10, pointerEvents: "none",
    background: "rgba(14,18,23,0.9)", border: "1px solid rgba(255,255,255,0.12)",
    borderRadius: 4, padding: "8px 10px", fontFamily: "var(--font-mono)", color: "#ECECE6",
  };
  const title: React.CSSProperties = { fontSize: 10, letterSpacing: "0.12em", color: "#6b7480", marginBottom: 6 };

  if (mode === "aqi")
    return (
      <div style={box}>
        <div style={title}>Air Quality Index</div>
        {AQI_STOPS.map((s, i) => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, lineHeight: "16px" }}>
            <span style={{ width: 11, height: 11, borderRadius: 2, display: "inline-block",
              background: `rgb(${interpRamp(AQI_FIELD, (i === 0 ? 25 : (AQI_STOPS[i - 1].max + s.max) / 2) / 500).join(",")})` }} />
            <span style={{ color: "#a7aeb6" }}>{s.label}</span>
            <span style={{ color: "#6b7480", marginLeft: "auto", paddingLeft: 10 }}>≤{s.max}</span>
          </div>
        ))}
      </div>
    );

  if (mode === "zones")
    return (
      <div style={box}>
        <div style={title}>K-Means pollution zones</div>
        <div style={{ width: 132, height: 9, borderRadius: 2, background: "linear-gradient(90deg, #6cb470, #e0cd66, #ee9a4e, #d65246, #874b9b)" }} />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#6b7480", marginTop: 4 }}>
          <span>lower AQI</span><span>higher AQI</span>
        </div>
        <div style={{ marginTop: 6, fontSize: 10, color: "#6b7480" }}>Relative clusters; not official CPCB bands.</div>
      </div>
    );

  if (mode === "isolation")
    return (
      <div style={box}>
        <div style={title}>Isolation Forest anomalies</div>
        <div style={{ color: "#ff7a45", fontSize: 12 }}>● anomalous HCHO feature vector</div>
        <div style={{ marginTop: 6, fontSize: 10, color: "#6b7480" }}>Unsupervised comparison baseline.</div>
      </div>
    );

  const rampStops = mode === "gas" ? FIELD_RAMP[gas] ?? FIELD_RAMP.hcho : FIELD_RAMP.hcho;
  const label = mode === "gas" ? `${GAS_LABEL[gas] ?? gas} column` : "HCHO column";
  return (
    <div style={box}>
      <div style={title}>{label}</div>
      <div style={{ width: 132, height: 9, borderRadius: 2, background: gradFromStops(rampStops) }} />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#6b7480", marginTop: 4 }}>
        <span>low</span><span>high</span>
      </div>
      {mode === "transport" && (
        <div style={{ marginTop: 8, fontSize: 11, color: "#a7aeb6", display: "flex", flexDirection: "column", gap: 3 }}>
          <span><span style={{ color: "#ff7a45" }}>—</span> back-trajectory</span>
          <span><span style={{ color: "#ff5a32" }}>●</span> fire pixel</span>
        </div>
      )}
    </div>
  );
}

function HotspotCard({ hotspot }: { hotspot: Hotspot | null }) {
  const h = hotspot ?? {
    lon: 77.1, lat: 28.65, source: "agri_burning", detail: "demo cluster", frp: 124, n: 8, _i: 0,
  };
  const confidence = confidenceFor(h);
  const id = h.id ?? `HCHO-${h.source.toUpperCase().slice(0, 4)}-${String((h._i ?? 0) + 1).padStart(3, "0")}`;
  return (
    <aside className="pointer-events-none absolute right-3 top-3 z-10 w-[min(320px,calc(100%-24px))] rounded-sm border p-4"
      style={{
        background: "rgba(14,18,23,0.92)",
        borderColor: "rgba(255,255,255,0.14)",
        color: "#ecece6",
        boxShadow: "0 18px 50px rgba(0,0,0,0.28)",
      }}>
      <div className="data text-[10px] uppercase" style={{ color: "#6b7480", letterSpacing: "0.14em" }}>Hotspot Intelligence</div>
      <div className="mt-3 flex items-start justify-between gap-3">
        <div>
          <div className="serif text-2xl capitalize leading-tight">{sourceLabel(h.source)}</div>
          <div className="data mt-1 text-[10px]" style={{ color: "#a7aeb6" }}>{id}</div>
        </div>
        <span className={`status-badge ${confidenceClass(confidence)}`}>{confidence}</span>
      </div>
      <div className="mt-4 grid gap-2 data text-[11px]" style={{ color: "#a7aeb6" }}>
        <div>Detail: {h.detail ?? "source attribution hypothesis"}</div>
        <div>Cluster size: {h.n ?? 1} cells</div>
        <div>FRP: {h.frp ?? 0} MW</div>
        <div>Coords: {h.lon.toFixed(2)}, {h.lat.toFixed(2)}</div>
      </div>
      <div className="mt-4 border-t pt-3 text-[12px] leading-5" style={{ borderColor: "rgba(255,255,255,0.12)", color: "#d6d8d2" }}>
        {SOURCE_ACTION[h.source] ?? SOURCE_ACTION.other}
      </div>
      {!hotspot && (
        <div className="data mt-3 text-[10px]" style={{ color: "#6b7480" }}>Hover a hotspot to inspect live demo evidence.</div>
      )}
    </aside>
  );
}

export function DeckMap({
  mode, frame = 0, gas = "hcho", height = 560, onReadout, aqiKind = "cpcb", onFrameCount,
}: {
  mode: Mode;
  frame?: number;
  gas?: string;
  height?: number;
  onReadout?: (s: string | null) => void;
  aqiKind?: "cpcb" | "rapi";   // which AQI index the 'aqi' mode colours by
  onFrameCount?: (n: number) => void;   // reports how many timelapse frames the AQI data actually has
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const overlay = useRef<MapboxOverlay | null>(null);
  const data = useRef<Record<string, unknown>>({});
  const props = useRef({ mode, frame, gas, aqiKind });
  const [layerStatus, setLayerStatus] = useState<LayerStatus>("loading");
  const [layerMessage, setLayerMessage] = useState("Loading atmospheric layer...");
  const [selectedHotspot, setSelectedHotspot] = useState<Hotspot | null>(null);
  props.current = { mode, frame, gas, aqiKind };

  const build = () => {
    const d = data.current as Record<string, any>;
    const { mode: m, frame: fr, gas: g, aqiKind: ak } = props.current;
    const layers: unknown[] = [];

    const HALF = 0.25; // 0.5° grid cell half-width (for the invisible pick grid)
    const cellPoly = (lon: number, lat: number) =>
      [[lon - HALF, lat - HALF], [lon + HALF, lat - HALF], [lon + HALF, lat + HALF], [lon - HALF, lat + HALF]];

    // Smooth field = BitmapLayer (GPU bilinear) + an invisible pickable grid for the hover readout.
    const field = (
      visPts: number[][], stops: Stop[], opts: FieldOpts, id: string,
      pickData?: number[][], pick = true,
    ) => {
      const f = buildField(visPts, stops, opts);
      if (f)
        layers.push(new BitmapLayer({
          id: `${id}-img`, image: f.image, bounds: f.bounds, opacity: 1, pickable: false,
          textureParameters: {
            minFilter: "linear", magFilter: "linear",
            addressModeU: "clamp-to-edge", addressModeV: "clamp-to-edge",
          },
        }));
      if (pick)
        layers.push(new PolygonLayer({
          id, data: pickData ?? visPts, getPolygon: (x: number[]) => cellPoly(x[0], x[1]),
          getFillColor: [0, 0, 0, 0], stroked: false, filled: true, pickable: true,
        }));
    };

    if (m === "aqi" && Array.isArray(d.aqi?.frames) && d.aqi.frames.length > 0) {
      const f = d.aqi.frames[Math.min(fr, d.aqi.frames.length - 1)];
      const vi = ak === "rapi" ? 3 : 2; // CPCB = column 2, RAPI = column 3
      if (Array.isArray(f?.cells))
        field(f.cells.map((c: number[]) => [c[0], c[1], c[vi]]), AQI_FIELD, { lo: 0, hi: 500 }, "aqi", f.cells);
    }
    if (m === "gas" && Array.isArray(d.gas?.cells)) {
      const pts = d.gas.cells.map((c: any) => [c.lon, c.lat, c[g]]);
      field(pts, FIELD_RAMP[g] ?? FIELD_RAMP.hcho, { lo: 0, hi: 1 }, "gas");
    }
    if (m === "zones" && Array.isArray(d.zones?.cells)) {
      const cells = d.zones.cells as ZoneCell[];
      layers.push(new PolygonLayer({
        id: "zones", data: cells,
        getPolygon: (x: ZoneCell) => cellPoly(x.lon, x.lat),
        getFillColor: (x: ZoneCell) => [...ZONE_RGB[x.zone_id % ZONE_RGB.length], 150] as [number, number, number, number],
        getLineColor: [255, 255, 255, 45], lineWidthMinPixels: 0.5,
        stroked: true, filled: true, pickable: true,
      }));
    }
    if (m === "hotspots" && Array.isArray(d.hcho)) {
      field(d.hcho, FIELD_RAMP.hcho, { lo: 0, hi: 1, aMin: 0.12, aMax: 0.6 }, "hcho-base", undefined, false);
      if (Array.isArray(d.hotspots)) {
        const hotspots = d.hotspots.map((x: Hotspot, i: number) => ({ ...x, _i: i }));
        layers.push(new ScatterplotLayer({
          id: "hotspots", data: hotspots,
          getPosition: (x: Hotspot) => [x.lon, x.lat],
          getRadius: (x: Hotspot) => 14000 + Math.sqrt(x.n ?? 1) * 9000, radiusUnits: "meters",
          radiusMinPixels: 4,
          getFillColor: (x: Hotspot) => [...(SOURCE_RGB[x.source] ?? SOURCE_RGB.other), 235] as [number, number, number, number],
          stroked: true, getLineColor: [255, 255, 255, 120], lineWidthMinPixels: 1, pickable: true,
          onClick: ({ object }: { object?: Hotspot }) => {
            if (object) setSelectedHotspot(object);
            return true;
          },
        }));
      }
    }
    if (m === "isolation") {
      if (Array.isArray(d.hcho)) field(d.hcho, FIELD_RAMP.hcho, { lo: 0, hi: 1, aMin: 0.08, aMax: 0.42 }, "hcho-base", undefined, false);
      if (Array.isArray(d.iso?.cells)) {
        const cells = d.iso.cells as IsolationCell[];
        layers.push(new ScatterplotLayer({
          id: "isolation", data: cells,
          getPosition: (x: IsolationCell) => [x.lon, x.lat],
          getRadius: (x: IsolationCell) => 9000 + Math.sqrt(x.cluster_size || 1) * 5000,
          radiusUnits: "meters", radiusMinPixels: 3,
          getFillColor: [255, 122, 69, 220], stroked: true,
          getLineColor: [255, 235, 200, 160], lineWidthMinPixels: 1, pickable: true,
        }));
      }
    }
    if (m === "transport") {
      if (Array.isArray(d.hcho)) field(d.hcho, FIELD_RAMP.hcho, { lo: 0, hi: 1, aMin: 0.08, aMax: 0.42 }, "hcho-base", undefined, false);
      if (Array.isArray(d.fires))
        layers.push(new ScatterplotLayer({
          id: "fires", data: d.fires, getPosition: (x: number[]) => [x[0], x[1]],
          getRadius: 9000, radiusUnits: "meters", radiusMinPixels: 1,
          getFillColor: [255, 90, 50, 180],
        }));
      if (Array.isArray(d.traj))
        layers.push(new PathLayer({
          id: "traj", data: [{ path: d.traj }], getPath: (x: any) => x.path,
          getColor: [255, 122, 69, 230], getWidth: 2.5, widthUnits: "pixels", capRounded: true,
        }));
    }
    return layers;
  };

  const tooltip = ({ object, layer }: any) => {
    if (!object) { onReadout?.(null); return null; }
    let txt = "";
    if (layer.id === "aqi") {
      const ak = props.current.aqiKind;
      const vi = ak === "rapi" ? 3 : 2;
      txt = `${ak === "rapi" ? "RAPI" : "AQI"} ${object[vi]} · ${object[0]}, ${object[1]}`;
    }
    else if (layer.id === "gas") txt = `${props.current.gas.toUpperCase()} ${(object[2] * 100).toFixed(0)}% · ${object[0]}, ${object[1]}`;
    else if (layer.id === "hotspots") {
      setSelectedHotspot(object as Hotspot);
      txt = `${object.source}${object.detail ? " / " + object.detail : ""} · FRP ${object.frp}`;
    }
    else if (layer.id === "zones") txt = `${object.zone_label} · AQI ${object.aqi ?? "n/a"} · ${object.lon}, ${object.lat}`;
    else if (layer.id === "isolation") txt = `Isolation anomaly ${(object.isolation_score ?? 0).toFixed(3)} · cluster ${object.cluster_id}`;
    onReadout?.(txt);
    return { html: `<div style="font:12px ui-monospace,monospace">${txt}</div>`,
      style: { background: "#0e1217", color: "#ECECE6", border: "1px solid rgba(255,255,255,.12)" } };
  };

  // init map once
  useEffect(() => {
    if (!wrap.current || map.current) return;
    const m = new maplibregl.Map({
      container: wrap.current, style: STYLE, center: [80.5, 22.5], zoom: 4,
      minZoom: 3.2, maxZoom: 8, attributionControl: false, dragRotate: false,
      maxBounds: [[58, -2], [104, 42]],
    });
    m.touchZoomRotate.disableRotation();
    m.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.current = m;
    m.on("load", async () => {
      setLayerStatus("loading");
      setLayerMessage("Loading atmospheric layer...");
      const need: Record<Mode, string[]> = {
        aqi: ["aqi_frames"], gas: ["gas_grids"],
        hotspots: ["hcho_grid", "hotspots"], transport: ["hcho_grid", "fires", "trajectory"],
        zones: ["zone_cells"], isolation: ["hcho_grid", "isolation_hotspots"],
      };
      const map2: Record<string, string> = {
        aqi_frames: "aqi", gas_grids: "gas", hcho_grid: "hcho",
        hotspots: "hotspots", fires: "fires", trajectory: "traj",
        zone_cells: "zones", isolation_hotspots: "iso",
      };
      const files = need[props.current.mode];
      const loaded = await Promise.all(files.map(async (f) => {
        try {
          const response = await fetch(`/data/${f}.json`);
          if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
          return { file: f, json: await response.json(), ok: true };
        } catch {
          return { file: f, json: null, ok: false };
        }
      }));
      if (map.current !== m) return; // unmounted (React strict-mode double-invoke)
      let ok = 0;
      loaded.forEach(({ file, json, ok: didLoad }) => {
        if (!didLoad) return;
        data.current[map2[file]] = json;
        ok += 1;
      });
      if (props.current.mode === "aqi") {
        const frames = (data.current.aqi as { frames?: unknown[] } | undefined)?.frames;
        onFrameCount?.(Array.isArray(frames) ? frames.length : 0);
      }
      if (ok === files.length) {
        setLayerStatus("ready");
        setLayerMessage("");
      } else if (ok > 0) {
        setLayerStatus("partial");
        setLayerMessage("Some prototype layers are unavailable.");
      } else {
        setLayerStatus("error");
        setLayerMessage("Layer unavailable in prototype mode.");
      }
      const ov = new MapboxOverlay({ interleaved: false, layers: build() as any, getTooltip: tooltip });
      m.addControl(ov as unknown as maplibregl.IControl);
      overlay.current = ov;
    });
    return () => { m.remove(); map.current = null; overlay.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // update layers on prop change
  useEffect(() => {
    overlay.current?.setProps({ layers: build() as any });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frame, gas, mode, aqiKind]);

  return (
    <div className="relative overflow-hidden rounded-sm" style={{ width: "100%", height }}>
      <div ref={wrap} style={{ width: "100%", height: "100%" }} />
      {layerStatus !== "ready" && (
        <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-sm border px-3 py-2 data text-[11px]"
          style={{
            background: "rgba(14,18,23,0.9)",
            borderColor: layerStatus === "error" ? "rgba(255,122,69,0.5)" : "rgba(255,255,255,0.12)",
            color: layerStatus === "loading" ? "#a7aeb6" : "#ffb48d",
          }}>
          {layerMessage}
        </div>
      )}
      {mode === "hotspots" && <HotspotCard hotspot={selectedHotspot} />}
      <MapLegend mode={mode} gas={gas} />
    </div>
  );
}
