import Link from "next/link";
import { Preloader } from "@/components/Preloader";
import { Hero } from "@/components/Hero";
import { MissionSnapshot } from "@/components/sections";
import { CHAPTERS } from "@/lib/chapters";

export default function Home() {
  return (
    <>
      <Preloader />
      <main>
        <Hero />
        <MissionSnapshot />
        <section className="mx-auto max-w-6xl px-6 py-24">
          <div className="eyebrow">Explore the investigation</div>
          <h2 className="display mt-3 text-[clamp(2rem,4vw,3.4rem)]">Choose a chapter.</h2>
          <p className="lede mt-4 max-w-2xl text-[clamp(1rem,1.3vw,1.2rem)]">
            Each chapter is its own page — open the one you want, instead of scrolling the whole story end to end.
          </p>
          <div
            className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-sm border sm:grid-cols-2 lg:grid-cols-3"
            style={{ borderColor: "var(--line)", background: "var(--line)" }}
          >
            {CHAPTERS.map((c) => (
              <Link
                key={c.href}
                href={c.href}
                className="metric-card group block no-underline transition-colors"
              >
                <div className="data text-[10px]" style={{ color: "var(--color-text-3)", letterSpacing: "0.14em" }}>
                  {c.num}
                </div>
                <div className="serif mt-4 text-[clamp(1.6rem,2.4vw,2.2rem)] leading-tight">{c.label}</div>
                <div className="data mt-3 text-[13px]" style={{ color: "var(--color-text-2)" }}>{c.desc}</div>
                <div className="data mt-6 text-[12px]" style={{ color: "var(--color-signal)" }}>Enter →</div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
