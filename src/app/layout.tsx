import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { OperationalProvider } from '@/context/OperationalContext';
import { AppShell } from '@/components/shell/AppShell';
import 'maplibre-gl/dist/maplibre-gl.css';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: 'SkyGuard AI | India AWS Meteorological Command Centre',
  description: 'National Automatic Weather Station anomaly detection and sensor-quality monitoring command platform (SIH Problem Statement 26073). Strict three-parameter physical contract: Temperature, Pressure, Relative Humidity.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`light ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased selection:bg-blue-100 selection:text-blue-900 font-sans">
        <OperationalProvider>
          <AppShell>
            {children}
          </AppShell>
        </OperationalProvider>
      </body>
    </html>
  );
}
