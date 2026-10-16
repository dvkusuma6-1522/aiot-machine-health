import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Environmental Monitoring & Climate Intelligence System",
  description: "Next-generation IoT climate telemetry, Random Forest air quality forecasting, and Isolation Forest anomaly detection.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-teal-500 selection:text-black min-h-screen">
        {children}
      </body>
    </html>
  );
}
