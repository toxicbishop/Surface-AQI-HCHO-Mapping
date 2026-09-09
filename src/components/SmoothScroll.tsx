"use client";

import { useEffect } from "react";
import Lenis from "lenis";

export function SmoothScroll() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      document.documentElement.classList.add("reduced-motion");
      return () => document.documentElement.classList.remove("reduced-motion");
    }

    const lenis = new Lenis({
      autoRaf: true,
      anchors: {
        offset: 0,
        duration: 1.05,
      },
      duration: 1.05,
      lerp: 0.085,
      wheelMultiplier: 0.82,
      touchMultiplier: 1.15,
      syncTouch: false,
      easing: (t) => Math.min(1, 1.001 - 2 ** (-10 * t)),
    });

    document.documentElement.classList.add("lenis-ready");

    return () => {
      document.documentElement.classList.remove("lenis-ready");
      lenis.destroy();
    };
  }, []);

  return null;
}
