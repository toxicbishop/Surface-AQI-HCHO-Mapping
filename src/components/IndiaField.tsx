"use client";
import { useEffect, useRef } from "react";
import {
  INDIA_POLY, project, pointInPolygon, intensityAt, aqiColor, intensityToAqi,
} from "@/lib/india";

type Mode = "atmos" | "aqi" | "hotspots" | "final";

/**
 * Canvas visual of India as a particle/heat field. Continuous advection/pulse is
 * a simulation (rAF); Anime.js drives all discrete reveals elsewhere. Honors
 * prefers-reduced-motion by rendering a single still frame.
 */
export function IndiaField({
  mode = "atmos",
  height = 560,
  className = "",
  season,
}: {
  mode?: Mode;
  height?: number;
  className?: string;
  season?: number; // 0..1 — if set, overrides the auto timelapse (AQI scrubber)
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const seasonRef = useRef<number | undefined>(season);
  useEffect(() => { seasonRef.current = season; }, [season]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0, h = 0;
    let pts: { lon: number; lat: number; v: number; ph: number }[] = [];

    const build = () => {
      const r = canvas.getBoundingClientRect();
      w = r.width; h = r.height || height;
      canvas.width = Math.max(1, w * dpr);
      canvas.height = Math.max(1, h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      pts = [];
      const step = mode === "atmos" ? 0.6 : 0.5;
      for (let lon = 68; lon <= 98; lon += step)
        for (let lat = 6; lat <= 37; lat += step)
          if (pointInPolygon(lon, lat))
            pts.push({ lon, lat, v: intensityAt(lon, lat), ph: Math.random() * Math.PI * 2 });
    };
    build();
    const ro = new ResizeObserver(build);
    ro.observe(canvas);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const outline = (alpha: number) => {
      ctx.beginPath();
      INDIA_POLY.forEach(([lon, lat], i) => {
        const [x, y] = project(lon, lat, w, h);
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      });
      ctx.closePath();
      ctx.strokeStyle = `rgba(255,122,51,${alpha})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    };

    let t = 0, raf = 0;
    const draw = () => {
      t += 0.016;
      ctx.clearRect(0, 0, w, h);
      outline(mode === "final" ? 0.1 : 0.18);
      const season =
        seasonRef.current ?? (reduce ? 0.6 : Math.sin(t * 0.25) * 0.5 + 0.5);
      for (const p of pts) {
        let [x, y] = project(p.lon, p.lat, w, h);
        let r = 2, a = 1, color = "rgba(255,122,51,0.5)";
        if (mode === "atmos") {
          if (!reduce) { x += Math.sin(t + p.ph) * 1.6; y += Math.cos(t * 0.8 + p.ph) * 1.2; }
          a = 0.18 + 0.45 * p.v; r = 1.3 + 1.7 * p.v;
          color = `rgba(255,150,80,${a})`;
        } else if (mode === "aqi" || mode === "final") {
          const aqi = intensityToAqi(Math.min(1, p.v * (0.55 + 0.6 * season)));
          color = aqiColor(aqi); a = mode === "final" ? 0.22 : 0.82; r = 3.1;
        } else if (mode === "hotspots") {
          if (p.v < 0.62) continue;
          const pulse = reduce ? 1 : Math.sin(t * 1.6 + p.ph) * 0.5 + 0.5;
          a = 0.4 + 0.5 * pulse; r = 3 + 3 * pulse * p.v;
          color = `rgba(255,122,69,${a})`;
        }
        ctx.globalAlpha = a;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    };

    const tick = () => {
      draw();
      raf = requestAnimationFrame(tick);
    };
    const start = () => {
      if (!raf && !reduce) raf = requestAnimationFrame(tick);
    };
    const stop = () => {
      if (!raf) return;
      cancelAnimationFrame(raf);
      raf = 0;
    };

    draw();
    if (!reduce) {
      const io = new IntersectionObserver((entries) => {
        const visible = entries.some((entry) => entry.isIntersecting);
        if (visible) start();
        else stop();
      }, { rootMargin: "220px 0px" });
      io.observe(canvas);
      start();
      return () => { stop(); io.disconnect(); ro.disconnect(); };
    }

    return () => { stop(); ro.disconnect(); };
  }, [mode, height]);

  return (
    <canvas ref={ref} className={className} style={{ width: "100%", height }} aria-hidden />
  );
}
