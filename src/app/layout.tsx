import type { Metadata } from 'next';
import Link from 'next/link';
import { Activity, BarChart3, CloudSun, RadioTower, ShieldCheck } from 'lucide-react';
import ServiceStatus from '@/components/service-status';
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
      <body className="min-h-screen flex flex-col text-slate-100">
        <header className="sky-header sticky top-0 z-50 border-b backdrop-blur-xl px-4 sm:px-7 py-3 flex flex-wrap items-center justify-between gap-3 lg:gap-5">
          <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-300/80 to-transparent" />
          <div className="flex items-center space-x-3">
            <Link href="/" className="flex items-center space-x-2.5 group">
              <span className="relative h-10 w-10 overflow-hidden rounded-xl bg-gradient-to-br from-cyan-300 via-blue-500 to-indigo-600 flex items-center justify-center font-black text-white shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
                <span aria-hidden="true" className="absolute inset-[1px] rounded-[11px] border border-white/25" />
                SG
              </span>
              <div>
                <div className="font-black text-white text-base tracking-tight flex items-center gap-2">
                  SkyGuard AI
                  <span className="text-[10px] uppercase font-extrabold tracking-[0.12em] px-1.5 py-0.5 rounded-md bg-cyan-400/10 text-cyan-300 border border-cyan-300/20">
                    SIH 26073
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 font-medium tracking-wide">Weather trust command centre</div>
              </div>
            </Link>
          </div>

          <nav aria-label="Primary navigation" className="sky-nav order-3 flex w-full items-center gap-1 overflow-x-auto rounded-xl p-1 text-xs font-semibold sm:text-sm lg:order-none lg:w-auto">
            <Link href="/" className="sky-nav-link inline-flex items-center gap-1.5 rounded-lg px-3 py-2">
              <CloudSun className="h-4 w-4 text-cyan-300" />
              Command Centre
            </Link>
            <Link href="/stations" className="sky-nav-link inline-flex items-center gap-1.5 rounded-lg px-3 py-2">
              <RadioTower className="h-4 w-4 text-blue-300" />
              AWS Network
            </Link>
            <Link href="/incidents" className="sky-nav-link inline-flex items-center gap-1.5 rounded-lg px-3 py-2">
              <Activity className="h-4 w-4 text-rose-300" />
              Incidents
            </Link>
            <Link href="/analytics" className="sky-nav-link inline-flex items-center gap-1.5 rounded-lg px-3 py-2">
              <BarChart3 className="h-4 w-4 text-emerald-300" />
              Analytics
            </Link>
            <Link href="/validation" className="sky-nav-link inline-flex items-center gap-1.5 rounded-lg px-3 py-2">
              <ShieldCheck className="h-4 w-4 text-violet-300" />
              25-Gate Validation
            </Link>
          </nav>

          <div className="flex items-center space-x-3">
            <ServiceStatus />
          </div>
        </header>

        <main className="relative z-10 flex-1 max-w-[1440px] w-full mx-auto p-4 sm:p-6 lg:px-8 lg:py-7">
          {children}
        </main>

        <footer className="relative border-t border-cyan-100/10 bg-[#050d18]/80 text-xs text-slate-400 py-6 px-4 sm:px-8 mt-12 backdrop-blur-lg">
          <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-400/30 to-transparent" />
          <div className="max-w-[1440px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <p className="font-bold text-slate-200">SkyGuard AI · Automatic Weather Station Anomaly Intelligence</p>
              <p className="text-slate-500 mt-0.5">Strict Three-Parameter Physical Contract: Temperature, Pressure, Relative Humidity</p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-slate-400">
              <span>Evidence-first</span>
              <span className="text-cyan-600">•</span>
              <span>Three-signal contract</span>
              <span className="text-cyan-600">•</span>
              <span>Vercel + Render</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
