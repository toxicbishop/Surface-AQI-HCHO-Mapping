// Chapter routing for the multi-page flow (landing hub + one page per chapter).
export type Chapter = { href: string; num: string; label: string; desc: string };

export const CHAPTERS: Chapter[] = [
  { href: "/problem", num: "01", label: "The Problem", desc: "Why most of India's air is unmeasured." },
  { href: "/method", num: "02", label: "The Method", desc: "Six satellite + ground streams, fused by a Random Forest predictor." },
  { href: "/aqi", num: "03", label: "AQI Map", desc: "Daily surface AQI across India — CPCB and RAPI." },
  { href: "/hcho", num: "04", label: "HCHO Hotspots", desc: "VOC anomalies, biomass burning and wind transport." },
  { href: "/model", num: "05", label: "Model & Accuracy", desc: "The Random Forest predictor, its validation and benchmarks." },
  { href: "/impact", num: "06", label: "Impact", desc: "Applications, policy actions and what comes next." },
];

export function chapterIndex(href: string): number {
  return CHAPTERS.findIndex((c) => c.href === href);
}
