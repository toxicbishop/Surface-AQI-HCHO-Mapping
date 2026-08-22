import { Section } from "@/components/Section";
import { Pipeline } from "@/components/Pipeline";
import { Observations } from "@/components/sections";
import { ChapterPager } from "@/components/ChapterNav";

export default function MethodPage() {
  return (
    <main>
      <Section
        id="pipeline"
        index="02"
        eyebrow="The Method"
        title="From raw signal to insight."
        lede="Six observation streams are fused, quality-screened, gridded and converted into AQI maps, HCHO anomaly layers and source-attribution hypotheses."
      >
        <Pipeline />
      </Section>
      <Observations />
      <ChapterPager current="/method" />
    </main>
  );
}
