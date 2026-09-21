import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "SmartWash",
  description: "Gestion operativa y fidelizacion para lavanderias",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" className="h-full">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
