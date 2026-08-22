"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CHAPTERS, chapterIndex } from "@/lib/chapters";

/** Sticky top navigation across the separate chapter pages. */
export function ChapterNav() {
  const path = usePathname();
  return (
    <header
      className="sticky top-0 z-50 border-b backdrop-blur"
      style={{ borderColor: "var(--line)", background: "color-mix(in srgb, var(--bg) 82%, transparent)" }}
    >
      <nav className="mx-auto flex max-w-6xl items-center gap-1 overflow-x-auto px-4 py-3">
        <Link href="/" className="serif mr-3 text-lg" style={{ color: "var(--color-signal)" }}>
          VAYU
        </Link>
        {CHAPTERS.map((c) => {
          const active = path === c.href;
          return (
            <Link
              key={c.href}
              href={c.href}
              aria-current={active ? "page" : undefined}
              className="data whitespace-nowrap rounded-full px-3 py-1.5 text-[12px] transition-colors"
              style={{
                color: active ? "#07090c" : "var(--color-text-2)",
                background: active ? "var(--color-signal)" : "transparent",
              }}
            >
              {c.num} · {c.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}

/** Prev / next pager shown at the bottom of each chapter page. */
export function ChapterPager({ current }: { current: string }) {
  const i = chapterIndex(current);
  const prev = i > 0 ? CHAPTERS[i - 1] : { href: "/", label: "Home" };
  const next = i >= 0 && i < CHAPTERS.length - 1 ? CHAPTERS[i + 1] : null;
  return (
    <div
      className="mx-auto flex max-w-6xl items-center justify-between gap-4 border-t px-6 py-12"
      style={{ borderColor: "var(--line)" }}
    >
      <Link href={prev.href} className="data text-[13px]" style={{ color: "var(--color-text-2)" }}>
        ← {prev.label}
      </Link>
      {next && (
        <Link
          href={next.href}
          className="data rounded-full px-5 py-2 text-[13px]"
          style={{ border: "1px solid var(--color-signal)", color: "var(--color-signal)" }}
        >
          {next.label} →
        </Link>
      )}
    </div>
  );
}
