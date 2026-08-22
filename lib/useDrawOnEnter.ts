"use client";
import { useEffect, useRef } from "react";
import { animate, createDrawable, cubicBezier, stagger, utils } from "animejs";

const DRAW_EASE = cubicBezier(0.65, 0, 0.35, 1);

/** Draws matching SVG paths (default `.draw`) once when the container enters view. */
export function useDrawOnEnter<T extends HTMLElement = HTMLDivElement>(selector = ".draw") {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const paths = el.querySelectorAll<SVGPathElement>(selector);
    if (!paths.length) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const draw = createDrawable(paths as unknown as SVGPathElement[]);
    if (reduce) return; // leave fully drawn
    utils.set(draw, { draw: "0 0" });
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        animate(draw, {
          draw: ["0 0", "0 1"], duration: 900,
          delay: stagger(140), ease: DRAW_EASE,
        });
      }),
      { threshold: 0.3 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [selector]);
  return ref;
}
