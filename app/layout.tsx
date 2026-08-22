import type { Metadata } from "next";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";
import { SmoothScroll } from "@/components/SmoothScroll";
import { ChapterNav } from "@/components/ChapterNav";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Footer } from "@/components/sections";

export const metadata: Metadata = {
  title: "VAYU — India's Air, Observed",
  description:
    "Development of Surface AQI & Identification of HCHO Hotspots over India using Satellite Data. A scientific documentary on India's air quality through satellites, atmospheric science, and deep learning.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <SmoothScroll />
        <ChapterNav />
        <ThemeToggle />
        {children}
        <Footer />
      </body>
    </html>
  );
}
