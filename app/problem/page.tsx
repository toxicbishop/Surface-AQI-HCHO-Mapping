import { AirQuality, Signals, WhySatellites } from "@/components/sections";
import { ChapterPager } from "@/components/ChapterNav";

export default function ProblemPage() {
  return (
    <main>
      <AirQuality />
      <Signals />
      <WhySatellites />
      <ChapterPager current="/problem" />
    </main>
  );
}
