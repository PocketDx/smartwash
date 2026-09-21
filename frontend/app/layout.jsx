import "./globals.css";

export const metadata = {
  title: "SmartWash",
  description: "Gestion operativa y fidelizacion para lavanderias",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es" className="h-full">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
