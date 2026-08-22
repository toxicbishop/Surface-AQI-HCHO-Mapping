"use client";
import { useEffect, useRef } from "react";
import { createScope, createTimeline, cubicBezier, stagger, utils } from "animejs";
import { IndiaField } from "./IndiaField";

const RESOLVE = cubicBezier(0.16, 1, 0.3, 1);

export function Hero() {
  const root = useRef<HTMLElement>(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const scope = createScope({ root: root.current! }).add(() => {
      utils.set(".hero-fade", { opacity: 0, translateY: 14 });
      if (reduce) {
        utils.set([".hero-fade", ".hero-line > span"], { opacity: 1, translateY: 0 });
        return;
      }
      const start = 2500; // reveal as the preloader lifts
      createTimeline({ defaults: { ease: RESOLVE } })
        .add(".hero-line > span", { translateY: ["110%", "0%"], duration: 950, delay: stagger(100) }, start)
        .add(".hero-eyebrow", { opacity: [0, 1], duration: 600 }, start)
        .add(".hero-sub", { opacity: [0, 1], translateY: [16, 0], duration: 700 }, start + 700)
        .add(".hero-cta", { opacity: [0, 1], translateY: [12, 0], duration: 600, delay: stagger(110) }, start + 1000);
    });
    return () => scope.revert();
  }, []);

  return (
    <section
      id="hero"
      ref={root}
      className="relative flex min-h-screen items-center overflow-hidden"
    >
      <div className="measure-grid pointer-events-none absolute inset-0 opacity-40" />
      {/* right: atmospheric India */}
      <div className="pointer-events-none absolute inset-y-0 right-0 w-full md:w-[58%]">
        <IndiaField mode="atmos" height={900} className="h-full" />
        <div
          className="absolute inset-0"
          style={{ background: "linear-gradient(90deg, var(--color-ink-900) 0%, transparent 55%)" }}
        />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-[1280px] px-6 md:px-16">
        <div className="hero-eyebrow eyebrow mb-6 flex items-center gap-3">
          <span style={{ color: "var(--color-signal)" }}>VAYU</span>
          <span className="hairline h-px w-10 border-t" />
          <span>INDIA · ATMOSPHERIC OBSERVATION</span>
        </div>
        <h1 className="display text-[clamp(2.6rem,7vw,6rem)]">
          <span className="reveal-line hero-line"><span>The Air You Breathe</span></span>
          <span className="reveal-line hero-line"><span>Has a Story.</span></span>
        </h1>
        <p className="hero-sub hero-fade lede mt-8 max-w-[520px] text-[clamp(1.05rem,1.6vw,1.4rem)]">
          A satellite-derived decision-support prototype for surface AQI,
          HCHO/VOC hotspots, fire influence and atmospheric transport over India.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-4">
          <a
            href="#mission-snapshot"
            className="hero-cta hero-fade data rounded-full px-7 py-3 text-[13px] font-medium transition-colors"
            style={{ border: "1px solid var(--color-signal)", color: "var(--color-signal)" }}
          >
            Start 90-second demo →
          </a>
          <a
            href="#pipeline"
            className="hero-cta hero-fade data px-2 py-3 text-[13px]"
            style={{ color: "var(--color-text-2)" }}
          >
            View Methodology
          </a>
        </div>
      </div>
    </section>
  );
}
