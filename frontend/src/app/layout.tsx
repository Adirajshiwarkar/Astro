import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aura Astrology - Celestial Alignment & In-Depth Forecasting",
  description: "A premium, human-centric astrological forecasting platform. Calculate natal charts, view personal timelines, and converse with our resident expert.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
