import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'SkyGuard AI | Intelligent AWS Anomaly Detection',
  description: 'AI-powered real-time anomaly detection and sensor-quality monitoring for Automatic Weather Stations (SIH 26073).',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#071521] text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
        <header className="sticky top-0 z-50 border-b border-[#1a4163] bg-[#0c2234]/90 backdrop-blur-md px-4 sm:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2.5 group">
              <span className="h-8 w-8 rounded-lg bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
                SG
              </span>
              <div>
                <div className="font-extrabold text-white text-base tracking-tight flex items-center gap-2">
                  SkyGuard AI
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                    SIH 26073
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 font-medium">Weather Network Command Centre</div>
              </div>
            </Link>
          </div>

          <nav className="flex items-center space-x-1 sm:space-x-2 text-xs sm:text-sm font-medium">
            <Link href="/" className="px-3 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-[#143652] transition-colors">
              Command Centre
            </Link>
            <Link href="/stations" className="px-3 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-[#143652] transition-colors">
              AWS Network
            </Link>
            <Link href="/incidents" className="px-3 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-[#143652] transition-colors">
              Incidents
            </Link>
            <Link href="/analytics" className="px-3 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-[#143652] transition-colors">
              Analytics
            </Link>
            <Link href="/validation" className="px-3 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-[#143652] transition-colors">
              25-Gate Validation
            </Link>
          </nav>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-[#071521] border border-emerald-500/30 text-emerald-400 text-xs font-mono">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span>Live Engine Connected</span>
            </div>
          </div>
        </header>

        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>

        <footer className="border-t border-[#1a4163] bg-[#071521] text-xs text-slate-400 py-6 px-4 sm:px-8 mt-12">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <p className="font-semibold text-slate-300">SkyGuard AI · Automatic Weather Station Anomaly Intelligence</p>
              <p className="text-slate-500 mt-0.5">Strict Three-Parameter Physical Contract: Temperature, Pressure, Relative Humidity</p>
            </div>
            <div className="flex items-center space-x-4 text-slate-400">
              <span>Phase 10 Compliant</span>
              <span>•</span>
              <span>Zero-Fake Validation</span>
              <span>•</span>
              <span>Vercel + Render Hybrid</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
