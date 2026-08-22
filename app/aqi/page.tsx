import { AQIIndia } from "@/components/sections";
import { ChapterPager } from "@/components/ChapterNav";

export default function AqiPage() {
  return (
    <main>
      <AQIIndia />
      <ChapterPager current="/aqi" />
    </main>
  );
}
