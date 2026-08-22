"use client";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("vayu-theme");
    const initial: "dark" | "light" =
      saved === "light" || saved === "dark"
        ? saved
        : window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    setTheme(initial);
    document.documentElement.dataset.theme = initial;
  }, []);

  const toggle = () => {
    const t = theme === "dark" ? "light" : "dark";
    setTheme(t);
    document.documentElement.dataset.theme = t;
    localStorage.setItem("vayu-theme", t);
  };

  return (
    <button
      onClick={toggle}
      aria-label="Toggle colour theme"
      className="data fixed right-4 top-4 z-50 rounded-full px-3 py-1.5 text-[11px]"
      style={{
        border: "1px solid var(--line)",
        background: "rgba(14,18,23,0.55)",
        color: "var(--color-text-2)",
        backdropFilter: "blur(6px)",
      }}
    >
      {theme === "dark" ? "◐ Light" : "◑ Dark"}
    </button>
  );
}
