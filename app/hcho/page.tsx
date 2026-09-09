"use client";
import { HCHO, Hotspots, Biomass, Transport } from "@/components/sections";
import { ChapterPager } from "@/components/ChapterNav";
import { LocationExplorer, useCellSelect } from "@/components/LocationExplorer";
import { CellSelectContext } from "@/lib/CellSelectContext";

export default function HchoPage() {
  const { cell, onCellSelect, onCellClose } = useCellSelect();
  return (
    <CellSelectContext.Provider value={onCellSelect}>
      <main className="relative">
        <div className="fixed inset-y-0 right-0 z-50 pointer-events-none">
          <div className="pointer-events-auto h-full">
            <LocationExplorer cell={cell ? { ...cell, dataStatus: "synthetic_demo" } : null} onClose={onCellClose} />
          </div>
        </div>
        <HCHO />
        <Hotspots />
        <Biomass />
        <Transport />
        <ChapterPager current="/hcho" />
      </main>
    </CellSelectContext.Provider>
  );
}
