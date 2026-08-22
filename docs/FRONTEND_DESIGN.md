# Frontend Experience Design
### "Development of Surface AQI & Identification of HCHO Hotspots over India using Satellite Data"
**Working codename: VAYU — *India's air, observed.*** *(वायु = air/wind)*

> **Design philosophy:** *Scientific elegance through motion and information hierarchy.*
> The site is not a dashboard wearing a story; it is a **documentary that behaves like a
> scientific instrument**. Every motion is calibrated, every number is a readout, every
> reveal is a measurement. Restraint is the aesthetic.

This document is the design bible: information architecture → visual system → motion
system → per-section UX & Anime.js choreography → component hierarchy → responsive
strategy → accessibility. **No code** — specifications, tokens, and named Anime.js v4
APIs only.

---

## 0. The central concept — "The Instrument"

Three ideas drive every decision:

1. **Instrument, not interface.** The shell evokes a calibrated scientific instrument:
   a faint measurement grid, tabular-mono readouts (coordinates, dates, concentrations),
   a single thin **scan line** motif that sweeps when data resolves. The UI never shouts;
   it *measures*.
2. **Two voices.** A documentary has a narrator and an instrument. We express this
   typographically: an **editorial serif** speaks the human story (headlines, lede,
   insights); a **technical mono/sans** speaks the data (labels, axes, metrics, units).
   Their interplay *is* "scientific elegance."
3. **Dark observatory ↔ light field-notebook.** The journey breathes between **dark
   "observation"** chapters (space, satellites, maps, night) and **light "explainer"**
   chapters (editorial teaching). This rhythm prevents monotony without gradients or
   glass. Both are fully designed (§II.9).

What we deliberately reject: glassmorphism, decorative gradients, floating-card grids,
drop-shadow soup, parallax abuse, bounce/elastic motion, fake-futuristic chrome, clutter.

---

# PART I — INFORMATION ARCHITECTURE

## I.1 Narrative arc

A single uninterrupted scroll, structured as a six-act documentary. The 17 mandated
sections map onto the arc:

| Act | Question it answers | Sections |
|-----|---------------------|----------|
| **0 · Ignition** | (entry) | 1 Preloader · 2 Hero |
| **I · Problem** | What is wrong, and why can't we see it? | 3 What is Air Quality · 4 Why Satellites |
| **II · Method** | How do we measure it? | 5 Data Pipeline · 6 Satellite Observations |
| **III · The Picture** | What does India's air look like? | 7 AQI over India |
| **IV · The Investigation** | The HCHO story | 8 Understanding HCHO · 9 HCHO Hotspots · 10 Biomass Burning · 11 Atmospheric Transport |
| **V · The Engine & Evidence** | Can we trust it? | 12 Model Architecture · 13 Results · 14 Research Insights |
| **VI · Consequence** | Why it matters | 15 Future Applications · 16 Final Impact · 17 Footer |

The emotional curve: *unease (invisible threat) → curiosity (how we see it) → awe (the
national picture) → understanding (the HCHO mechanism) → trust (the science) →
resolve (we can act).*

## I.2 The scroll spine & global navigation

- **Chapter Rail** (persistent, desktop): a hairline vertical rail pinned left
  (24px from edge). 17 tick marks = chapters; the active tick grows and shows a mono
  label on hover; a thin **progress fill** tracks global scroll. Doubles as a jump menu.
  This is the only persistent chrome — it reads as an instrument's measurement scale.
- **Readout header** (top-right, persistent, minimal): live mono micro-readout that
  reflects the current chapter context (e.g. `CHAPTER 07 / AQI · INDIA · 2019–2023`),
  plus theme toggle and a "Methodology" anchor. Collapses to a single dot on scroll-down,
  re-expands on scroll-up.
- **No mega-nav, no hamburger clutter.** Mobile collapses the rail into a bottom
  progress bar + a chapter sheet.

## I.3 Loading & streaming behavior (global)

- **One cinematic preloader** (§1) — the *only* full-screen loader. No spinners anywhere
  else, no percentage theater.
- **Progressive hydration:** narrative/text sections render instantly (SSR/Next.js).
  Heavy viz (MapLibre, deck.gl, R3F) are **lazy-mounted on viewport approach** (rootMargin
  ~40vh) behind a quiet skeleton that is just the final layout's hairline frame + a
  single sweeping scan line — never a spinner.
- **Asset budget:** map tiles and the AQI raster stacks are tiled/pyramided; only the
  active layer + adjacent timeline frames are fetched. Preconnect to tile/data origins.
- **Scroll is the clock.** Scrubbed scenes (pipeline, transport, timelapse) are driven by
  scroll position, so "loading" of a scene = its data being range-fetched ahead of the
  scrub head.

---

# PART II — VISUAL DESIGN SYSTEM

## II.1 Typography hierarchy

**Typefaces** (premium primary → free fallback):
- **Editorial serif — "Tiempos Headline" / fallback *Newsreader*.** Headlines, lede,
  pull-quotes, insights. Weights 400/500. This is the *narrator*.
- **Editorial text serif — "Tiempos Text" / *Newsreader* 400/420 optical.** Long-form
  explainer body (HCHO, insights).
- **UI sans — "Söhne" / fallback *Inter*.** Nav, buttons, captions, UI labels, legends.
  400/500/600.
- **Technical mono — "Söhne Mono" / fallback *IBM Plex Mono*.** All data: coordinates,
  dates, units, metrics, axis labels, the readout header. `font-variant-numeric:
  tabular-nums`. This is the *instrument*.

**Type scale** (desktop; fluid via `clamp()` between mobile→desktop):

| Token | Font | Size / Line | Use |
|-------|------|-------------|-----|
| Display-XL | serif 500 | 96 / 1.02 | Hero, Final Impact |
| Display-L | serif 500 | 64 / 1.05 | Act openers |
| H1 | serif 500 | 48 / 1.08 | Section titles |
| H2 | serif 400 | 36 / 1.15 | Sub-headlines |
| H3 | sans 600 | 24 / 1.25 | Component titles |
| Lede | serif 400 | 22 / 1.5 | Section intros |
| Body | serif 400 | 18 / 1.6 | Explainer prose |
| Body-UI | sans 400 | 16 / 1.5 | UI copy |
| Caption | sans 500 | 14 / 1.4 | Captions, legends |
| Data | mono 400 | 13 / 1.3 tabular | Readouts, axes |
| Label | sans 600 | 12 / 1.0, tracking +0.10em, UPPERCASE | Eyebrows, chapter ids |

**Rules:** max measure 66ch for serif body; numbers/units always mono; eyebrow Labels
precede every section title (e.g. `CHAPTER 03 — THE METRIC`). Letne­spacing tight on
display serif (−0.01em), open on Labels.

## II.2 Spacing system

8px base unit. Scale: **4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96 · 128 · 160 · 240**.
Section vertical padding: **desktop 160 / tablet 112 / mobile 72**. Vertical rhythm
snaps to an 8px baseline. Whitespace is a primary material — explainer sections are
generous; observation (map) sections go edge-to-edge.

## II.3 Grid system

- **Desktop (≥1280):** 12 columns, max content width 1440, outer margin 64, gutter 24.
  Editorial text occupies cols 3–9 (asymmetric); maps and pipeline go **full-bleed**.
- **Tablet (768–1279):** 8 columns, margin 40, gutter 20.
- **Mobile (<768):** 4 columns, margin 20, gutter 16.
- An optional **Measurement Grid overlay** (the "graph-paper" motif): a 1px grid at 8%
  opacity that *fades in only during data moments* — never always-on.

## II.4 Color palette — core (dark primary)

| Token | Hex | Use |
|-------|-----|-----|
| Ink-900 | `#07090C` | Page background ("deep atmosphere") |
| Ink-800 | `#0E1217` | Raised surfaces / map void |
| Ink-700 | `#161B22` | Panels, sheets |
| Ink-600 | `#222A33` | Strong lines, dividers |
| Hairline | `rgba(255,255,255,.08)` | Default borders, grid |
| Text-1 | `#ECECE6` | Primary text (warm off-white) |
| Text-2 | `#A7AEB6` | Secondary |
| Text-3 | `#6B7480` | Tertiary, captions |
| **Signal** | `#5FE3D2` | *The only accent.* Active states, scan line, focus, live data. Used <5% of any view. |
| Signal-dim | `#2E7C74` | Hover rests, inactive accent |
| Ember | `#FF7A45` | Reserved for fire/HCHO heat accents only |

Discipline: neutrals carry 95% of the interface; **Signal** marks "the system is live /
this is interactive"; **Ember** appears only where the science is literally about heat.

## II.5 AQI palette (CPCB National AQI — data fidelity is non-negotiable)

Legends, the AQI atlas, and any reported value use the **official CPCB** hex (matches
national reporting; do not "prettify" data):

| Band | AQI | Official CPCB | Display-refined* |
|------|-----|---------------|------------------|
| Good | 0–50 | `#009865` | `#4FB477` |
| Satisfactory | 51–100 | `#84CF33` | `#A7CC4D` |
| Moderate | 101–200 | `#FFFB26` | `#F2C53D` |
| Poor | 201–300 | `#F2A93B` | `#EC9A3C` |
| Very Poor | 301–400 | `#EA3324` | `#DB5247` |
| Severe | 401–500 | `#9C2E2C` | `#8C2F2C` |

\* The *display-refined* set (calmer, perceptually smoother) is permitted **only** for
ambient/branding moments (hero wash, Final Impact). **Every legend and map stays
official CPCB.** This honesty is part of the credibility.

## II.6 Map palette

- **Dark basemap** (default): custom minimal MapLibre style — land `#0C1014`, water
  `#070A0D`, internal boundaries hairline `#2A333D`, **India national boundary** lifted
  to `#3A4753`, sparse mono labels `#8A929B`. Almost no labels; the data is the subject.
- **Light basemap:** land `#F1EFEA`, water `#E3E6E4`, boundaries `#C9C8C1`.
- **Perceptually-uniform ramps only — never rainbow/jet** (scientific correctness, and we
  say so in legends):
  - **AOD** → custom "haze" sequential (transparent → `#E8C39E` → `#8A5A2B`).
  - **NO₂** → magma-family (deep purple → magenta → cream).
  - **HCHO** → `YlOrRd` (continuity with the project's analysis figures).
  - **SO₂ / CO / O₃** → viridis / cividis (color-blind safe), one per pollutant for
    instant recognition.
  - **Fire / FRP** → inferno.
  - **Wind vectors** → monochrome **Signal** cyan on dark; particle advection same hue.
- Raster layers render at 70–85% opacity over the void so the basemap geography stays
  legible; legends carry the ramp + units (mono).

## II.7 Data-visualization palette (charts)

Categorical, color-blind-safe (Okabe–Ito refined): `#5FE3D2` (model), `#E0A458`
(observed/CPCB), `#8AB4F8`, `#C792EA`, `#7FBF7F`, `#E57373`. Model-vs-observed always
= **Signal (model)** vs **warm sand (observed)** for instant reading. Sequential ramps
reuse the viridis family. Gridlines hairline; axes mono; no chart junk, no 3-D, no pies.

## II.8 Iconography & illustration

- **Line-only**, 1.5px stroke, 24px grid, geometric, drawn (not filled). Pollutant and
  application icons share one construction logic so they feel instrument-engraved.
- Scientific illustrations (molecules, chemical chains, satellite, CNN-LSTM) are
  **schematic line art** — engraving/blueprint aesthetic, never 3-D-render kitsch.

## II.9 Dark & light modes

- **Dark is primary** (observatory). **Light** is a true alternate (field notebook), not
  an afterthought: Paper `#F7F6F1`, surface `#FFFFFF`, lines `rgba(0,0,0,.10)`, Text-1
  `#14181D`, Text-2 `#4A525B`; **Signal deepens to `#0E8576`**, Ember to `#D94A1F` for
  contrast. Maps swap to the light basemap; data ramps unchanged (they're data).
- Some chapters are *intrinsically* dark (1, 2, 6, 7, 9, 11, 16 — space/maps); in light
  mode these become "deep slate" `#10151B` panels rather than pure black, preserving the
  observation feel while respecting the user's choice.
- Toggle persists (localStorage) and respects `prefers-color-scheme` on first visit.

## II.10 Accessibility & WCAG

- **WCAG 2.2 AA** target. Body text ≥ 4.5:1, large text/UI ≥ 3:1; Signal-on-Ink and all
  AQI legend text verified (AQI swatches always paired with a text/value label — **never
  color-only**, critical for color-blind users).
- Full keyboard path; visible **Signal** focus ring (2px + 2px offset); skip-to-content;
  logical heading order (one H1 per section as `aria-labelledby`).
- Maps/charts have text/table equivalents (`<figure>`+`<figcaption>`, a "view data"
  disclosure with the underlying numbers); deck.gl canvases get `role="img"` + rich alt.
- `prefers-reduced-motion` is a first-class branch (§III.6).
- Sliders/scrubbers are real ARIA `slider`s (arrow-key steppable, value announced).
- Target sizes ≥ 24×24 (AA) / 44×44 on touch.

---

# PART III — MOTION DESIGN SYSTEM

## III.1 Motion language

*Instrument motion.* Things **resolve** and **settle**; they don't spring. Reveals feel
like a plotter drawing, a sensor sweeping, a value converging. Three motion archetypes:

1. **Resolve** — content fades + rises a short distance and settles (entrances).
2. **Plot** — SVG strokes draw along their path (orbits, trajectories, connections,
   chemical chains, neural links).
3. **Advect** — continuous, slow ambient drift (atmospheric particles, wind, timelapse).

## III.2 Duration tokens (ms)

`instant 120 · quick 200 · base 360 · slow 600 · narrative 900 · epic 1400`;
ambient loops `6000–12000`. Scrubbed scenes have **no intrinsic duration** (mapped to
scroll). Nothing one-shot exceeds `epic`.

## III.3 Easing tokens (cubic-bézier)

| Token | Curve | Use |
|-------|-------|-----|
| `ease-resolve` | `cubic-bezier(.16,1,.30,1)` | Entrances/reveals (calm settle) |
| `ease-standard` | `cubic-bezier(.40,0,.20,1)` | UI state changes, hovers |
| `ease-exit` | `cubic-bezier(.40,0,1,1)` | Departures |
| `ease-plot` | `cubic-bezier(.65,0,.35,1)` | SVG path draws, morphs |
| `ease-scrub` | `linear` | Scroll-linked scenes |

**Prohibited:** `easeOutBounce`, `easeOutElastic`, `back.*`, overshoot of any kind.

## III.4 Stagger strategy

- Text lines: `stagger(60ms)`. List/insight items: `stagger(80ms)`.
- Pollutant emergence / icon grids: `stagger(90ms)` sequential.
- Particle fields: `stagger(12–20ms, { grid:[cols,rows], from:'center' })` for radial
  resolves.
- Map glyphs / hotspots: `stagger(25ms, { from:'first' })`, capped so total ≤ 900ms.

## III.5 Anime.js v4 implementation strategy (primary engine)

Anime.js v4 is the sole animation engine (Framer Motion only for trivial layout
presence if unavoidable; **GSAP & Lottie prohibited**).

- **`createScope({ root })`** wraps each animated React section → automatic
  `scope.revert()` on unmount (no leaks, SSR-safe; animations declared inside the scope).
- **`onScroll({ target, container, sync, enter, leave })`** is the backbone:
  - `sync: true` (or a smoothing value) → **scrubbed** scenes bound to scroll progress
    (Pipeline, Satellite layers, AQI timelapse, Biomass split, Transport draw, Model
    reveal). Replaces GSAP ScrollTrigger natively.
  - `enter:'bottom-=15% top'` thresholds → **one-shot reveals** (text, charts).
- **`createTimeline()`** choreographs multi-step sequences (Preloader, Hero, pollutant
  walk, chemical chains); timelines are seekable so the same timeline can be *played*
  (one-shot) or *scrubbed* (`timeline.seek(progress * timeline.duration)`).
- **`svg.createDrawable(selector)`** → line drawing via `draw:['0 0','0 1']` (orbit,
  trajectories, neural/pipeline links, molecule bonds).
- **`svg.morphTo()`** → legend/scale morphs, India outline state changes, glyph swaps.
- **`stagger()`** as in §III.4. **`createAnimatable()`** for cursor-reactive node/layer
  expansion (Pipeline nodes, Model layers) — smooth pointer-follow without re-renders.
- **`utils.mapRange` / `utils.lerp` / `utils.clamp`** map scroll progress → any param.
- **Bridging to viz libs:** Anime.js animates a plain JS *driver object* (e.g.
  `{t:0, opacity:0}`); its `onUpdate`/`onRender` pushes values into **deck.gl**
  (`setProps`/layer `transitions`, `updateTriggers`), **MapLibre** (`setPaint`,
  `easeTo` for camera), and **D3** scales (re-render axes/legends). Crossfades = animate
  two stacked deck layers' opacity in a timeline. **R3F** scenes read the same driver via
  `useFrame`.
- **Cleanup/perf:** one shared rAF (Anime.js engine) ; pause off-screen scopes via the
  same IntersectionObserver that lazy-mounts viz; `will-change` only during active
  tweens.

## III.6 Global replay & reduced-motion policy

- **One-shot reveals do not auto-replay** on scroll-back (prevents twitch); they hold
  their resolved state. Exceptions: ambient loops persist; scrubbed scenes always mirror
  the scroll head (bidirectional).
- **`prefers-reduced-motion: reduce`** → a global branch: all `Resolve`/`Plot`/`Advect`
  collapse to **opacity-only 200ms** fades; ambient loops and particle advection stop at
  a representative still frame; scrubbed scenes become **stepped** (snap between key
  states) and remain fully usable; the preloader shortens to a 600ms logo/India fade.

---

# PART IV — SECTION-BY-SECTION UX & MOTION

*Each section lists: Purpose · Layout (desktop) · Typography · Interactions · Scroll ·
Anime.js spec (Trigger / Duration / Easing / Stagger / Viewport / Replay) · Loading ·
Responsive (tablet, mobile).*

---

### SECTION 1 — PRELOADER  *(Act 0 · dark)*
- **Purpose:** anticipation; establish the instrument tone in one breath.
- **Layout:** full-viewport Ink-900. Centered SVG stage; a single mono readout line
  bottom-center (`ESTABLISHING ORBIT…` → `RESOLVING AQI FIELD…`), no percentages.
- **Typography:** one Label line (mono 12, Text-3); wordmark resolves at the end.
- **Sequence (one `createTimeline`):**
  1. **Satellite orbit path draws** (`svg.createDrawable`, `draw 0→1`).
  2. **India outline draws** along its stroke, then fills to a faint plate.
  3. **Pollution particles emerge** (`stagger` grid from orbit point).
  4. **AQI heatmap resolves** (particles settle into the CPCB ramp / low-res field).
  5. **Hand-off:** stage scales ~1.04 + fades; India + first hero frame persist into §2
     (shared-element continuity — the preloader's India *becomes* the hero's India).
- **Anime spec —** Trigger: on mount. Duration: **3.0–3.6s total** (orbit 700 · India
  600 · particles 700 · heatmap 700 · handoff 500). Easing: `ease-plot` (draws),
  `ease-resolve` (settles), `ease-exit` (handoff). Stagger: particles `12ms` grid from
  center. Viewport: blocks first paint of below content until step 4 begins (content
  pre-hydrates beneath). Replay: never (session-flagged; returning visitors get the 600ms
  short form).
- **Loading:** real assets (fonts, hero map tiles, first AQI frame) preload *during* the
  sequence; if ready early, the timeline still completes its minimum (no jarring cut); if
  slow past 4s, hold step 4's ambient loop until ready (still no numbers).
- **Responsive:** tablet/mobile identical choreography, smaller stage; mobile reduces
  particle count ~60% and shortens to ~2.6s.

---

### SECTION 2 — HERO  *(Act 0 · dark)*
- **Purpose:** "Air pollution is invisible. Its consequences are not."
- **Layout:** full-viewport split. **Left (cols 1–6):** headline, subheadline, dual CTA.
  **Right (cols 7–12):** live atmospheric India visualization (deck.gl particle/density
  field over the dark basemap, inherited from preloader).
- **Typography:** Display-XL serif headline *"The Air You Breathe Has a Story."*;
  Lede serif subhead; Label eyebrow `INDIA · ATMOSPHERIC OBSERVATION`.
- **Interactions:** pointer parallax on the field is **minimal** (≤6px); CTAs —
  **Explore Air Quality** (primary, Signal outline) and **View Methodology** (ghost).
  Subtle pointer attraction of nearby particles (advect toward cursor, capped).
- **Scroll:** a short scroll fades the lede and drifts the field back, cueing descent.
- **Anime spec —** Trigger: preloader hand-off (chained timeline). Duration: headline
  lines `narrative 900` each, sub `slow 600`, CTAs `base 360`. Easing: `ease-resolve`.
  Stagger: headline **line-by-line `stagger(80ms)`** (mask-reveal), CTAs `stagger(90ms)`.
  Ambient: particle **advect loop 9000ms** + slow density **pulse 6000ms** (opacity
  0.6↔0.9). Viewport: plays once on load. Replay: ambient persists; text holds.
- **Loading:** field initialized during preloader; degrades to a static density image if
  WebGL unavailable.
- **Responsive:** **Tablet** — stack: headline over a 16:9 field. **Mobile** — headline
  first, compact field below, single full-width primary CTA + text-link secondary;
  particle count halved; parallax off.

---

### SECTION 3 — WHAT IS AIR QUALITY  *(Act I · light)*
- **Purpose:** teach AQI + the 6 pollutants visually — **no cards**, a horizontal
  storytelling timeline.
- **Layout:** a pinned, horizontally-progressing **scrollytelling track**. A fixed left
  rail holds the running concept (AQI definition + a live AQI dial); the right 70% is a
  horizontal lane where pollutants (PM2.5, PM10, NO₂, SO₂, CO, O₃) arrive one at a time,
  each a schematic line illustration with **Source / Health impact / AQI influence**
  (mono micro-stats).
- **Typography:** H2 serif per pollutant name; mono stat triplet; serif micro-explainer.
- **Interactions:** vertical scroll advances the horizontal lane (scroll-jacked within
  the pinned span, with a clear progress sub-rail and an escape at the end). Each
  pollutant's "AQI influence" bar animates to its weight; hovering a pollutant dims the
  others.
- **Scroll:** **scrubbed** — pollutant index = `mapRange(sectionProgress)`.
- **Anime spec —** Trigger: `onScroll({ sync })` over the pinned span. Duration: per
  pollutant resolve `slow 600` (illustration draws + stats count up). Easing: `ease-plot`
  (illustration strokes), `ease-resolve` (stats). Stagger: stat triplet `60ms`; the six
  pollutants gated by scroll, not time. Viewport: enters when section pins. Replay: state
  follows scroll both directions; illustrations stay drawn once passed.
- **Loading:** SVG illustrations inline (tiny); no external assets.
- **Responsive:** **Tablet** — horizontal lane becomes a snap-scroll carousel (swipe).
  **Mobile** — convert to a **vertical** stepped sequence (one pollutant per ~80vh,
  enter-reveal), AQI dial pinned as a slim top bar; no scroll-jacking on touch.

---

### SECTION 4 — WHY SATELLITES  *(Act I · dark)*
- **Purpose:** ground stations are too sparse; satellites see everywhere.
- **Layout:** centered India map, full-bleed. Two scroll beats: **(a)** sparse CPCB
  station dots appear with Voronoi "blind spots"; **(b)** satellite coverage **sweeps**
  across and fills the nation.
- **Typography:** H1 serif statement that swaps mid-section: *"~X stations for 1.4
  billion people."* → *"Most people live far beyond a monitor."* Mono station counter.
- **Interactions:** hovering a station shows its coverage radius; a toggle "Stations ↔
  Satellite" lets the user replay the contrast.
- **Scroll:** beat (a) reveal on enter; beat (b) **scrubbed** coverage fill.
- **Anime spec —** Trigger: enter (a) + `onScroll sync` (b). Duration: stations
  `stagger(25ms)` over ~700ms; coverage sweep scrubbed (a vertical/curved wipe of a
  coverage raster). Easing: `ease-resolve` (dots), `ease-scrub` (sweep). Stagger: dots
  from-first; blind-spot Voronoi fades in after. Viewport: 25% in. Replay: toggle re-runs
  the sweep timeline.
- **Loading:** station GeoJSON (small) + one coverage raster.
- **Responsive:** **Tablet** identical, fewer station labels. **Mobile** — map fills
  width; the two beats become two tap/scroll steps; statement text above map.

---

### SECTION 5 — PROJECT DATA PIPELINE  *(Act II · dark · CENTERPIECE)*
- **Purpose:** the methodology, as a cinematic system diagram.
- **Layout:** full-bleed horizontal **node graph**. Left column = **inputs** (INSAT-3D,
  Sentinel-5P, ERA5, CPCB, VIIRS, MODIS); flowing right through stages **Raw → Processing
  → Deep Learning → AQI Generation → Hotspot Detection**. Nodes are precise line glyphs;
  edges are drawable paths; **data particles** travel along edges.
- **Typography:** mono node labels + dataset metadata (resolution, cadence) revealed on
  expand; H2 serif section title pinned top-left.
- **Interactions:** **hover/focus a node → it expands** (`createAnimatable` scale +
  detail panel: what it is, its role, its real asset id/units). Clicking an input
  highlights its full downstream path (edges + nodes light in **Signal**).
- **Scroll:** **scrubbed assembly** — as the user scrolls, nodes appear, then edges
  **draw**, then particles begin to flow; reaching the end leaves the whole system live
  and gently animating.
- **Anime spec —** Trigger: `onScroll({ sync })` for assembly; ambient particle loop
  after. Duration: nodes `base 360` each (staggered by scroll), edge draws `narrative
  900` (`svg.createDrawable`), particle advection loop `8000ms`. Easing: `ease-resolve`
  (nodes), `ease-plot` (edges), `linear` (particles). Stagger: inputs `90ms`; edges draw
  in dependency order. Viewport: pins for the assembly span. Replay: assembly mirrors
  scroll; particle loop persists; hover-expand is on-demand.
- **Loading:** pure SVG/Canvas; no external data (it's a diagram of the system).
- **Responsive:** **Tablet** — graph rotates to a vertical top-down flow, still drawable.
  **Mobile** — vertical stepped flow, one stage per screen; particles simplified to a
  single moving glyph; tap a node to expand in a bottom sheet.

---

### SECTION 6 — SATELLITE OBSERVATIONS  *(Act II · dark)*
- **Purpose:** show the actual datasets; let users switch layers.
- **Layout:** full-bleed India map + a **layer switcher** (AOD · NO₂ · CO · SO₂ · O₃ ·
  HCHO) as a horizontal mono segmented control; a morphing legend (ramp + units) bottom-
  left; date stamp mono top-right.
- **Typography:** mono layer labels & legend; H3 caption describing the active variable.
- **Interactions:** select a layer → **crossfade** raster; legend ramp **morphs** to the
  new palette/scale; hovering the map shows a mono readout tooltip (lat, lon, value, unit).
- **Scroll:** enter-reveal of frame; layer changes are user-driven (not scrubbed).
- **Anime spec —** Trigger: user select. Duration: raster crossfade `slow 600`; legend
  morph `slow 600`; scale-tick reflow `base 360`. Easing: `ease-standard`. Stagger: legend
  ticks `40ms`. Viewport: lazy-mount on approach. Replay: every switch; **no abrupt
  cuts** — outgoing layer fades as incoming resolves (two deck layers, opposed opacity
  via one timeline). Reduced-motion: instant swap + 120ms opacity.
- **Loading:** tiled rasters per variable; prefetch the adjacent layer on hover intent.
- **Responsive:** **Tablet** — switcher wraps; legend docks bottom. **Mobile** — switcher
  becomes a swipeable chip row; tap-to-read value (no hover); one layer at a time.

---

### SECTION 7 — AQI OVER INDIA  *(Act III · dark · FLAGSHIP)*
- **Purpose:** the predicted-AQI flagship visualization.
- **Layout:** maximal India map (near full-viewport). Bottom: a single elegant
  **time scrubber** with three nested granularities — **Date · Month · Season** (segmented
  mode switch). CPCB legend fixed; a mono readout shows current frame + national mean AQI.
- **Typography:** mono timeline ticks/labels; H1 serif overline *"India, breathing."*
- **Interactions:** drag the scrubber → **time-lapse AQI** animates smoothly; play/pause;
  mode switch reframes the timeline; click a region → mono callout with its AQI + dominant
  pollutant. **No chart clutter** — the map is the chart.
- **Scroll:** entering pins the map; an initial auto-played sweep (one season) invites,
  then hands control to the user.
- **Anime spec —** Trigger: enter → brief auto-timelapse; then user-driven. Duration:
  frame-to-frame raster tween `base 360` (interpolated), full auto-sweep ~`6000ms`.
  Easing: `linear` while dragging (`ease-standard` for play). Stagger: n/a (field tween).
  Viewport: pin while active. Replay: fully bidirectional with the scrubber; auto-sweep
  plays once on first enter.
- **Loading:** AQI raster pyramid; only frames around the scrub head + look-ahead are
  fetched; interpolate between keyframe dates for smoothness.
- **Responsive:** **Tablet** — map + bottom scrubber, season/month default (date on
  demand). **Mobile** — full-width map, scrubber as a large touch slider, default to
  **monthly** frames to bound data; pinch-zoom enabled, region callouts as bottom sheet.

---

### SECTION 8 — UNDERSTANDING HCHO  *(Act IV · light)*
- **Purpose:** teach formaldehyde from first principles — a layered explainer.
- **Layout:** editorial two-column: serif prose left (cols 3–7), an evolving **schematic
  reaction stage** right (cols 8–12) that builds as the prose advances —
  *VOCs → (oxidation) → HCHO → (sunlight + NOₓ) → O₃*, with the biomass-burning input
  branching in.
- **Typography:** Lede + Body serif; mono molecular labels (HCHO, NO₂, O₃, OH·).
- **Interactions:** as each paragraph enters, the corresponding **bond/arrow draws** and
  the molecule assembles; hovering a species shows a one-line mono definition.
- **Scroll:** **scrubbed** chain — reaction progress = section progress.
- **Anime spec —** Trigger: `onScroll sync`. Duration: each bond/arrow draw `slow 600`
  (`svg.createDrawable`); molecule assembly `narrative 900`. Easing: `ease-plot`.
  Stagger: atoms `90ms`, bonds in reaction order. Viewport: per-paragraph gates. Replay:
  follows scroll; completed chain holds.
- **Loading:** inline SVG; nil external.
- **Responsive:** **Tablet** — prose over stage, stage 16:9. **Mobile** — alternating
  prose/stage steps; each reaction step its own ~70vh enter-reveal (no scrub).

---

### SECTION 9 — HCHO HOTSPOTS  *(Act IV · dark · FINDINGS)*
- **Purpose:** present detected hotspots with clear hierarchy.
- **Layout:** full-bleed India map. **Primary** hotspots = larger, Signal/Ember halo;
  **secondary** = smaller, dimmer. Kernel-density layer beneath. A **year selector**
  (mono segmented) top-right; legend distinguishes primary/secondary + density.
- **Typography:** H1 serif *"Where the air turns reactive."*; mono hotspot callouts
  (name, lat/lon, HCHO column, source class from the analysis: agri-burning / urban /
  industrial).
- **Interactions:** select year → density + points **re-resolve**; hover a hotspot →
  callout + its attributed source; toggle "Density ↔ Points."
- **Scroll:** density layer emerges on enter; hotspots resolve after.
- **Anime spec —** Trigger: enter + year select. Duration: density raster fade `slow
  600`; hotspots **subtle pulse loop 4000ms** (scale 1↔1.06, opacity 0.7↔1 — *never*
  flash); point resolve `stagger(25ms)`. Easing: `ease-resolve` (in), `ease-standard`
  (pulse). Stagger: primaries first, then secondaries. Viewport: lazy-mount. Replay: year
  change re-runs resolve; pulse is the only persistent loop. **No flashing/strobe.**
- **Loading:** per-year density rasters + hotspot GeoJSON (from `hcho_hotspots_attributed`).
- **Responsive:** **Tablet** — same; year selector wraps. **Mobile** — default to density
  view (legible at small size), tap hotspots for sheet; pulse amplitude reduced.

---

### SECTION 10 — BIOMASS BURNING IMPACT  *(Act IV · dark)*
- **Purpose:** show fire → HCHO cause-and-effect.
- **Layout:** **split-screen.** Left = fire activity (VIIRS/MODIS points + FRP). Right =
  HCHO concentration field. A shared time axis links both.
- **Typography:** mono synchronized date; H2 serif beat captions ("Stubble season
  begins…", "HCHO responds…"); mono correlation readout (r, lag).
- **Interactions:** as the user scrolls the shared timeline, **fire counts rise on the
  left and HCHO brightens on the right in lockstep**, making the correlation viscerally
  obvious; a small linked spark-pair (fire count vs HCHO) tracks beneath.
- **Scroll:** **scrubbed**, both panels driven by one progress value.
- **Anime spec —** Trigger: `onScroll({ sync })` driving one timeline → both deck scenes.
  Duration: scrubbed; fire-point emergence `stagger(20ms)` gated by scroll; HCHO field
  opacity/intensity tween `ease-scrub`. Easing: `linear` (scrub). Stagger: fires from
  source clusters outward. Viewport: pins for the linked span. Replay: bidirectional.
- **Loading:** time-binned fire points + HCHO frames; range-fetched around scrub head.
- **Responsive:** **Tablet** — split becomes top/bottom. **Mobile** — top/bottom stack,
  shorter timeline, stepped scrub (snap to key dates) for performance.

---

### SECTION 11 — ATMOSPHERIC TRANSPORT  *(Act IV · dark · SHOWPIECE)*
- **Purpose:** pollution *moves* — the section should feel extraordinary.
- **Layout:** full-viewport India, deep night basemap. **Animated wind vectors / particle
  advection** across the country; **transport trajectories draw progressively**
  (Punjab → Delhi; forest fires → downwind). Minimal mono annotations at endpoints.
- **Typography:** Display-L serif *"The air carries it."*; mono trajectory labels
  (origin → receptor, transit time h).
- **Interactions:** select a corridor (e.g. *Punjab → Delhi*) → its trajectory draws and
  particles intensify along it; hover endpoints for mono detail; a subtle wind-field
  toggle.
- **Scroll:** wind field advects ambiently; trajectories **draw on scroll** (scrubbed),
  then persist.
- **Anime spec —** Trigger: ambient field loop on enter; `onScroll sync` for trajectory
  draws (`svg.createDrawable` over the curved great-circle-ish paths) + deck particle
  intensity. Duration: each trajectory draw `epic 1400`; wind advection loop `10000ms`.
  Easing: `ease-plot` (draw), `linear` (advection). Stagger: corridors `120ms`. Viewport:
  pins for the draw span. Replay: corridor re-select re-draws; field persists. Motion is
  **subtle, realistic** — slow, no jitter.
- **Loading:** ERA5 wind field (downsampled vectors) + precomputed trajectory paths.
- **Responsive:** **Tablet** — fewer particles, same draws. **Mobile** — static-ish wind
  hint + tap-to-draw a corridor; particle count heavily reduced; trajectory draw on tap,
  not scroll.

---

### SECTION 12 — MODEL ARCHITECTURE  *(Act V · dark)*
- **Purpose:** explain CNN-LSTM for non-experts.
- **Layout:** horizontal interactive diagram: **Satellite Data → CNN (spatial) →
  Temporal Memory (LSTM) → AQI Prediction.** Each stage is a schematic block; a **signal**
  travels left→right through it.
- **Typography:** H3 sans stage titles; serif one-liner per stage ("The CNN reads the
  *shape* of pollution…"); mono tensor shapes on expand.
- **Interactions:** **hover a layer → detail reveal** (what it does, why); a "Run a
  sample" control sends a signal pulse through the network end-to-end, lighting layers in
  sequence and ending on a predicted AQI value.
- **Scroll:** **scrubbed layer-by-layer reveal** on first pass; interactive afterward.
- **Anime spec —** Trigger: `onScroll sync` (reveal) → interactive. Duration: per-layer
  reveal `slow 600`; **neural signal** traversal `narrative 900` (`svg.createDrawable`
  along connections + node flares). Easing: `ease-resolve` (reveal), `ease-plot` (signal).
  Stagger: layers `90ms`; intra-layer nodes `20ms` grid. Viewport: pins for reveal.
  Replay: "Run a sample" replays the signal on demand; reveal holds.
- **Loading:** pure SVG/Canvas.
- **Responsive:** **Tablet** — vertical flow. **Mobile** — vertical stepped stages;
  "Run a sample" becomes a single tap that animates the vertical chain; tensor details in
  sheets.

---

### SECTION 13 — RESULTS  *(Act V · light)*
- **Purpose:** present achievements with maximum clarity, minimum chart.
- **Layout:** editorial. A headline metric band (**R² · RMSE · MAE**, mono, large) over a
  restrained **observed-vs-predicted** scatter (Signal=model, sand=CPCB) + a small
  validation map (predicted vs station points). Per-pollutant small-multiples kept lean;
  SO₂/CO honestly flagged as lower-confidence.
- **Typography:** Display-L mono for headline numbers (count-up); serif captions; mono
  axis labels.
- **Interactions:** hover scatter point → station detail; toggle pollutant; a "vs CPCB"
  switch overlays station truth.
- **Scroll:** **animation only on viewport entry** (per the brief).
- **Anime spec —** Trigger: enter (one-shot). Duration: metrics **count-up `narrative
  900`**; scatter points fade/resolve `slow 600`; the 1:1 line **draws** `slow 600`.
  Easing: `ease-resolve`, `ease-plot` (line). Stagger: metrics `80ms`; scatter `8ms` grid.
  Viewport: 30% in. Replay: none (holds).
- **Loading:** small JSON of metrics + sampled validation points.
- **Responsive:** **Tablet** — metrics row over single scatter. **Mobile** — metrics
  stack (still count-up), scatter simplified (hexbin density), small-multiples become a
  swipe.

---

### SECTION 14 — RESEARCH INSIGHTS  *(Act V · light)*
- **Purpose:** summarize discoveries — large editorial layout, **no cards**.
- **Layout:** magazine-grade editorial spread. Each insight = a full-width band: a giant
  serif statement (*"The Indo-Gangetic Plain is a persistent reactive corridor."*) with a
  supporting mono stat and a small inline figure (sparkline / mini-map) bleeding into the
  margin. Insights: highest-AQI regions · persistent hotspots · seasonal burning impact ·
  transport findings.
- **Typography:** H1/Display-L serif statements; mono evidence; serif micro-context.
- **Interactions:** minimal — inline figures animate on entry; an optional "see the data"
  reveals the underlying number/table.
- **Scroll:** each band enter-reveals.
- **Anime spec —** Trigger: enter per band. Duration: statement line-mask `narrative 900`;
  inline figure draw `slow 600`; stat count-up `slow 600`. Easing: `ease-resolve`,
  `ease-plot`. Stagger: statement lines `80ms`. Viewport: 25% in. Replay: none.
- **Loading:** text + tiny inline SVG/figures.
- **Responsive:** **Tablet/Mobile** — bands stack naturally; inline figures move below
  their statement; type scales down but stays editorial.

---

### SECTION 15 — FUTURE APPLICATIONS  *(Act VI · light)*
- **Purpose:** where this goes — NCAP · Urban Planning · Public Health · Climate
  Monitoring · ISRO Applications · Smart Cities.
- **Layout:** a quiet 3×2 (desktop) lattice on the measurement grid — **not floating
  cards**; each item is an engraved line **icon** + label + one serif line, separated by
  hairlines (a "field index," not a card deck).
- **Typography:** H3 sans labels; serif one-liners; Label eyebrow `APPLICATIONS`.
- **Interactions:** hover → icon line **draws/strokes** + the one-liner reveals; click →
  optional deeper note.
- **Scroll:** items resolve in reading order on entry.
- **Anime spec —** Trigger: enter. Duration: icon stroke draw `slow 600`; label/line
  `base 360`. Easing: `ease-plot` (icons), `ease-resolve` (text). Stagger: `90ms` across
  the lattice (from top-left). Viewport: 25% in. Replay: hover re-strokes its icon.
- **Loading:** inline SVG icons.
- **Responsive:** **Tablet** 3×2→2×3; **Mobile** single column, icon-left/text-right rows
  divided by hairlines.

---

### SECTION 16 — FINAL IMPACT  *(Act VI · dark)*
- **Purpose:** the emotional landing.
- **Layout:** full-viewport. Centered Display-XL serif statement **"We cannot improve
  what we cannot see."** over a **subtle, slow** background animation of India's AQI
  evolving (the timelapse from §7, dimmed and de-saturated so text dominates).
- **Typography:** Display-XL serif; a single Label line beneath (project + ISRO credit).
- **Interactions:** none beyond an optional "Begin again ↑" / "Methodology →".
- **Scroll:** statement reveals on entry; background loops gently.
- **Anime spec —** Trigger: enter. Duration: statement word-mask reveal `epic 1400`;
  background AQI evolution **ambient loop 12000ms** at low contrast. Easing: `ease-resolve`
  (text), `linear` (background). Stagger: words `120ms`. Viewport: 40% in. Replay: text
  holds; background loops. **Subtle, non-distracting** — background ≤ 30% luminance of the
  text.
- **Loading:** reuse §7 frames at low res.
- **Responsive:** identical; mobile reduces background frame rate and statement to 3 lines.

---

### SECTION 17 — FOOTER  *(Act VI · dark)*
- **Purpose:** credits, data, methodology, publications, contact — clean, minimal.
- **Layout:** a precise multi-column index on the measurement grid: **Research credits ·
  Datasets (INSAT-3D, Sentinel-5P, ERA5, CPCB, MODIS/VIIRS, WorldCover, SRTM) ·
  Methodology (link to the phase docs) · Publications · Contact.** A final hairline + mono
  colophon (build, data vintage, license).
- **Typography:** Label column heads; mono links/metadata; serif one-line mission
  restatement.
- **Interactions:** link hovers = Signal underline draw (left→right); dataset rows expand
  to show asset id/resolution (mono).
- **Scroll:** simple enter fade; the Chapter Rail's last tick rests here.
- **Anime spec —** Trigger: enter. Duration: columns fade/rise `base 360`. Easing:
  `ease-resolve`. Stagger: columns `80ms`; link underline `quick 200` on hover. Viewport:
  20% in. Replay: hovers only.
- **Loading:** static.
- **Responsive:** columns collapse to an accordion-free stacked list; mono colophon last.

---

# PART V — COMPONENT HIERARCHY

```
<ExperienceRoot>                      theme, scroll-progress, reduced-motion, anime engine
├─ <Preloader/>                       (session-gated)
├─ <ChapterRail/>                     persistent progress + jump (desktop)
├─ <ReadoutHeader/>                   live mono context + theme toggle
├─ <MeasureGridOverlay/>             motif, opacity-driven by scroll moments
├─ <ScanLine/>                        shared sweep motif
└─ <Story>                            the scroll spine
   ├─ <Section variant="dark|light"> generic chapter shell (eyebrow, title, padding)
   │   └─ section organisms (Hero, AQIPrimer, WhySatellites, …, Footer)
   │
   ├─ Narrative primitives
   │   ├─ <Heading> <Lede> <Prose>            serif voices
   │   ├─ <DataLabel> <Metric> <Readout>      mono instrument voices
   │   ├─ <Eyebrow>  <PullStatement>
   │   ├─ <Button variant="primary|ghost">
   │   └─ <Hairline> <Legend> <Scrubber> <SegmentedControl>
   │
   ├─ Visualization layer (lazy-mounted)
   │   ├─ <IndiaMap>          MapLibre style wrapper (dark/light)
   │   │   └─ <DeckOverlay>   deck.gl layer host (driver-object bridge)
   │   ├─ <RasterLayer/> <HotspotLayer/> <DensityLayer/>
   │   ├─ <StationLayer/> <CoverageSweep/>
   │   ├─ <WindField/> <TrajectoryPaths/>     advection + drawable SVG
   │   ├─ <TimeScrubber/>     date/month/season modes
   │   ├─ <LayerSwitcher/> <MapLegend/>       crossfade + morph
   │   ├─ <PipelineGraph/>   nodes/edges/particles (SVG+Canvas)
   │   ├─ <ChemChain/>       drawable reaction stage
   │   ├─ <ModelDiagram/>    CNN-LSTM, signal traversal
   │   └─ <MetricChart/> <ScatterObsPred/> <Sparkline/>   (D3 scales + Anime)
   │
   └─ Motion utilities
       ├─ useAnimeScope()    createScope per section + revert on unmount
       ├─ useScrollScene()   onScroll({sync}) wrapper → driver object
       ├─ useReveal()        enter one-shot timelines
       └─ useReducedMotion() global branch
```

Design-token layer (Tailwind theme + CSS vars): `--ink-*`, `--text-*`, `--signal`,
`--aqi-*`, spacing/type/easing/duration tokens consumed by both Tailwind and Anime.js.

---

# PART VI — RESPONSIVE STRATEGY

**Approach: desktop-first** (the experience is authored for large observation screens),
with deliberate tablet and mobile *re-choreography* — not just reflow.

- **Breakpoints:** Desktop ≥1280 · Tablet 768–1279 · Mobile <768 (plus ≥1920 "wall"
  that simply increases map bleed + type max-steps).
- **Global tablet rules:** 8-col grid; horizontal scrollytelling (§3) → swipe carousels;
  split-screens (§10) → stacked; Chapter Rail → top progress bar; particle counts −40%.
- **Global mobile rules:**
  - **No scroll-jacking on touch.** Every scrubbed scene degrades to a **stepped,
    enter-reveal or tap-driven** sequence (the brief's "scroll → story" intent preserved
    without janky pinning).
  - Maps are **tap-to-explore** (no hover): values via tap → bottom sheet; default to
    coarser time granularity (monthly) and lower-res rasters to bound data/CPU.
  - Particle/WebGL budgets cut ~60%; ambient loops slowed; non-essential advection paused
    off-screen.
  - Type scale steps down one level; editorial measure → 38–42ch; CTAs full-width.
  - Chapter Rail → bottom progress bar + a chapter sheet (swipe-up index).
- **Performance guardrails (all breakpoints):** lazy-mount viz on viewport approach;
  one shared rAF; pause off-screen scopes; `content-visibility:auto` on below-fold
  sections; raster pyramids + range-fetch for timelapse; WebGL feature-detect with static
  image fallbacks; respect Save-Data + reduced-motion.

---

# PART VII — SUMMARY OF MOTION CONTRACTS (quick reference)

| Section | Primary motion | Driver | Replay |
|---------|----------------|--------|--------|
| 1 Preloader | orbit/India/particles/heatmap draw+resolve | timeline (once) | never |
| 2 Hero | line-mask headline + particle advect | timeline + loop | text holds / loop |
| 3 Air Quality | pollutant walk | scroll-sync (pinned) | bidirectional |
| 4 Satellites | station stagger + coverage sweep | enter + scroll-sync | toggle |
| 5 Pipeline | node assemble + edge draw + particles | scroll-sync + loop | scroll / loop |
| 6 Observations | raster crossfade + legend morph | user event | every switch |
| 7 AQI India | timelapse field tween | scrubber + auto-once | bidirectional |
| 8 HCHO | reaction chain draw | scroll-sync | scroll |
| 9 Hotspots | density fade + subtle pulse | enter + loop | year re-resolve |
| 10 Biomass | fire↑ / HCHO↑ lockstep | scroll-sync | bidirectional |
| 11 Transport | wind advect + trajectory draw | loop + scroll-sync | corridor re-draw |
| 12 Model | layer reveal + signal traverse | scroll-sync → interactive | on demand |
| 13 Results | metric count-up + scatter resolve | enter (once) | none |
| 14 Insights | statement line-mask + figure draw | enter (per band) | none |
| 15 Applications | icon stroke draw | enter + hover | hover re-stroke |
| 16 Final | word-mask + dim AQI loop | enter + loop | text holds / loop |
| 17 Footer | column resolve + link underline | enter + hover | hover |

---

*Build order recommendation:* design tokens + `<ExperienceRoot>`/scroll plumbing →
narrative primitives → `<IndiaMap>` + deck bridge → flagship §7 → centerpiece §5 →
showpiece §11 → remaining chapters → preloader/hero polish → accessibility + reduced-
motion pass → performance hardening. Everything in this document is specification; no
implementation code is included by design.
