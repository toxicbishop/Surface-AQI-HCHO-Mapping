import { HCHO, Hotspots, Biomass, Transport } from "@/components/sections";
import { ChapterPager } from "@/components/ChapterNav";

export default function HchoPage() {
  return (
    <main>
      <HCHO />
      <Hotspots />
      <Biomass />
      <Transport />
      <ChapterPager current="/hcho" />
    </main>
  );
}
