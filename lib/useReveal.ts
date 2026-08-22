"use client";
import { useEffect, useRef } from "react";
import { animate, cubicBezier, stagger } from "animejs";

const RESOLVE = cubicBezier(0.16, 1, 0.3, 1);

/**
 * One-shot enter reveal for any container. Animates direct children that carry
 * [data-reveal] (and lines that carry .reveal-line > span). Plays once when the
 * element enters the viewport; respects prefers-reduced-motion (CSS handles it).
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(opts?: {
  y?: number;
  stagger?: number;
  threshold?: number;
}) {
  const ref = useRef<T>(null);
  const played = useRef(false);
  const { y = 24, stagger: stg = 80, threshold = 0.2 } = opts ?? {};

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting || played.current) return;
          played.current = true;
          io.disconnect();

          const items = el.querySelectorAll<HTMLElement>("[data-reveal]");
          const lines = el.querySelectorAll<HTMLElement>(".reveal-line > span");

          if (reduce) {
            items.forEach((i) => (i.style.opacity = "1"));
            return;
          }
          if (lines.length) {
            animate(lines, {
              translateY: ["110%", "0%"],
              duration: 900,
              delay: stagger(70),
              ease: RESOLVE,
            });
          }
          if (items.length) {
            animate(items, {
              opacity: [0, 1],
              translateY: [y, 0],
              duration: 700,
              delay: stagger(stg),
              ease: RESOLVE,
            });
          }
        });
      },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [y, stg, threshold]);

  return ref;
}
