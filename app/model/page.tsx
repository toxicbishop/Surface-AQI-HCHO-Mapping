import { Section } from "@/components/Section";
import { Model, Results, Insights } from "@/components/sections";
import { ChapterPager } from "@/components/ChapterNav";

const ACCURACY: [string, string, string][] = [
  ["PM2.5 · PM10", "R² 0.53 · 0.58", "random CV · RMSE 60 / 92 µg/m³"],
  ["NO₂", "R² 0.71", "random CV · near India target 0.83"],
  ["O₃", "R² 0.66", "beats India target 0.60"],
  ["SO₂ · CO", "R² 0.46 · 0.69", "meet / beat targets 0.40 · 0.58"],
  ["Spatial CV", "R² 0.02–0.19", "held-out regions — the honest extrapolation floor"],
  ["Data status", "REAL ✓", "161 CPCB stations · 4,382 station-days · Oct–Dec 2025"],
];

export default function ModelPage() {
  return (
    <main>
      <Section
        id="model-accuracy"
        index="05"
        eyebrow="Model & Accuracy"
        title="How accurate is it — and how do we know?"
        lede="A Random-Forest trend learns surface pollutant levels from the daily satellite + meteorology stack (TROPOMI gases, MAIAC AOD, ERA5). It's validated against 161 real CPCB stations (via OpenAQ, Oct–Dec 2025) two ways: random cross-validation — held-out days at known stations, how the literature reports skill — and spatial cross-validation — held-out regions, the hard test of predicting where there are no monitors."
      >
        <div
          className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-sm border sm:grid-cols-2 lg:grid-cols-3"
          style={{ borderColor: "var(--line)", background: "var(--line)" }}
        >
          {ACCURACY.map(([k, v, s]) => (
            <div key={k} className="metric-card">
              <div className="data text-[10px] uppercase" style={{ color: "var(--color-text-3)", letterSpacing: "0.14em" }}>{k}</div>
              <div className="serif mt-3 text-[clamp(1.4rem,2.2vw,2rem)] leading-none">{v}</div>
              <div className="data mt-3 text-[12px]" style={{ color: "var(--color-text-2)" }}>{s}</div>
            </div>
          ))}
        </div>
        <p className="data mt-6 text-[12px]" style={{ color: "var(--color-text-3)" }}>
          Benchmarks are India-competitive targets from the literature (Wang 2023; Katoch 2023; Science Advances 2024).
          Under random CV the model meets or beats the India benchmark for SO₂, O₃ and CO, and is solid for NO₂ and PM —
          on real CPCB ground truth, not synthetic. Spatial extrapolation to unmonitored regions (the objective&apos;s core
          challenge) stays hard, and the honest gap between random and spatial CV shows exactly that. The live AQI map is now
          this model&apos;s real prediction (4,329 cells).
        </p>
      </Section>
      <Model />
      <Results />
      <Insights />
      <ChapterPager current="/model" />
    </main>
  );
}
