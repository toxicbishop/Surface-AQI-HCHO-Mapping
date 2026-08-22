"use client";
import { ReactNode } from "react";
import { useReveal } from "@/lib/useReveal";

export function Section({
  id,
  index,
  eyebrow,
  title,
  lede,
  variant = "dark",
  children,
  grid = false,
}: {
  id: string;
  index: string;
  eyebrow: string;
  title: ReactNode;
  lede?: ReactNode;
  variant?: "dark" | "paper";
  children?: ReactNode;
  grid?: boolean;
}) {
  const ref = useReveal<HTMLDivElement>();
  return (
    <section
      id={id}
      data-chapter={index}
      className={`relative ${variant === "paper" ? "panel-paper" : ""}`}
    >
      {grid && (
        <div className="measure-grid pointer-events-none absolute inset-0 opacity-50" />
      )}
      <div
        ref={ref}
        className="relative mx-auto max-w-[1280px] px-6 py-[120px] md:px-16 md:py-[160px]"
      >
        <div className="max-w-[820px]">
          <div className="eyebrow mb-5 flex items-center gap-3" data-reveal>
            <span>{index}</span>
            <span className="hairline h-px w-10 border-t" />
            <span>{eyebrow}</span>
          </div>
          <h2 className="display text-[clamp(2rem,5vw,3.25rem)]">
            {typeof title === "string" ? (
              <span className="reveal-line">
                <span>{title}</span>
              </span>
            ) : (
              title
            )}
          </h2>
          {lede && (
            <p
              className="lede mt-6 max-w-[640px] text-[clamp(1.05rem,1.6vw,1.35rem)]"
              data-reveal
            >
              {lede}
            </p>
          )}
        </div>
        {children}
      </div>
    </section>
  );
}
