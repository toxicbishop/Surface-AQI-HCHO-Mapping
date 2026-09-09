"use client";
import { createContext, useContext } from "react";

export type CellSelectHandler = (info: {
  lon: number; lat: number;
  aqi?: number; hcho?: number;
  zoneLabel?: string; zoneId?: number;
  isolationScore?: number;
  source?: string;
  nearbyFireCount?: number; nearbyFRP?: number;
}) => void;

/** Pages that want to show the LocationExplorer wrap their content in this provider. */
export const CellSelectContext = createContext<CellSelectHandler | null>(null);

export function useCellSelectContext(): CellSelectHandler | null {
  return useContext(CellSelectContext);
}
