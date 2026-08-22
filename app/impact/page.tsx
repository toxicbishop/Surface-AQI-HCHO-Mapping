import { PolicyActionBoard, Evidence, Future, FinalImpact } from "@/components/sections";
import { ChapterPager } from "@/components/ChapterNav";

export default function ImpactPage() {
  return (
    <main>
      <PolicyActionBoard />
      <Evidence />
      <Future />
      <FinalImpact />
      <ChapterPager current="/impact" />
    </main>
  );
}
