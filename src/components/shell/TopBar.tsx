'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { 
  Bell, 
  ChevronDown, 
  Clock, 
  Command, 
  Globe, 
  HelpCircle, 
  Menu,
  Radio, 
  Search, 
  ShieldCheck, 
  SlidersHorizontal 
} from 'lucide-react';
import { WorkingViewFilter } from '@/lib/types';

interface TopBarProps {
  timeMode: 'UTC' | 'IST';
  setTimeMode: (mode: 'UTC' | 'IST') => void;
  activeView: WorkingViewFilter;
  setActiveView: (view: WorkingViewFilter) => void;
  onOpenCommandPalette: () => void;
  onToggleMobileMenu?: () => void;
  engineStatus?: 'OPERATIONAL' | 'DEGRADED' | 'OFFLINE';
  lastObservationUtc?: string;
}

export function TopBar({
  timeMode,
  setTimeMode,
  activeView,
  setActiveView,
  onOpenCommandPalette,
  onToggleMobileMenu,
  engineStatus = 'DEGRADED',
  lastObservationUtc,
}: TopBarProps) {
  const [viewDropdownOpen, setViewDropdownOpen] = useState(false);
  const [aboutModalOpen, setAboutModalOpen] = useState(false);

  const viewLabels: Record<WorkingViewFilter, string> = {
    ALL_INDIA: 'All India station catalog',
    NORTH_INDIA: 'North Region (Indo-Gangetic & Himalayas)',
    SOUTH_INDIA: 'South Region (Peninsula & Coastal)',
    EAST_INDIA: 'East & North-East Region',
    WEST_CENTRAL: 'West & Central Plateau',
    CRITICAL_STATIONS: 'Critical Anomaly Focus',
    ACTIVE_INCIDENTS: 'Stations with Active Incidents',
    HOLDOUT_SET: 'Unseen Station Holdout Set (Evaluation)',
  };

  return (
    <>
      <header className="sticky top-0 z-40 w-full bg-white/95 backdrop-blur-md border-b border-slate-200 px-3 md:px-4 py-2.5 flex items-center justify-between gap-2 md:gap-3 text-slate-800 select-none shadow-sm">
        {/* Left: Mobile Toggle + Logo & Crest */}
        <div className="flex items-center gap-2 md:gap-3">
          {onToggleMobileMenu && (
            <button
              onClick={onToggleMobileMenu}
              className="md:hidden p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-slate-200 transition-colors"
              aria-label="Toggle navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="relative w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 via-indigo-600 to-sky-500 flex items-center justify-center font-black text-white text-xs shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
              <span className="absolute inset-0.5 rounded-[6px] border border-white/30" />
              <Radio className="w-4 h-4 text-white animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 font-black text-slate-900 text-sm tracking-tight leading-none">
                <span>SkyGuard AI</span>
                <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded-md bg-blue-50 text-blue-700 border border-blue-200 font-bold">
                  SIH 26073
                </span>
              </div>
              <p className="text-[10px] text-slate-500 font-mono tracking-tight mt-0.5">
                India AWS Meteorological Command Centre
              </p>
            </div>
          </Link>

          {/* Workspace / View Selector */}
          <div className="relative hidden md:block ml-3">
            <button
              onClick={() => setViewDropdownOpen(!viewDropdownOpen)}
              className="flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200/70 border border-slate-200 transition-colors text-slate-700 shadow-sm"
            >
              <Globe className="w-3.5 h-3.5 text-blue-600" />
              <span>{viewLabels[activeView]}</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 ml-1" />
            </button>

            {viewDropdownOpen && (
              <div 
                className="absolute top-full left-0 mt-1.5 w-72 bg-white border border-slate-200 rounded-xl shadow-2xl py-1 z-50 text-xs"
                onMouseLeave={() => setViewDropdownOpen(false)}
              >
                <div className="px-3 py-1.5 font-bold text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100">
                  Operational Working Views
                </div>
                {(Object.keys(viewLabels) as WorkingViewFilter[]).map((viewKey) => (
                  <button
                    key={viewKey}
                    onClick={() => {
                      setActiveView(viewKey);
                      setViewDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 flex items-center justify-between hover:bg-blue-50/70 transition-colors ${
                      activeView === viewKey ? 'text-blue-700 font-bold bg-blue-50/50' : 'text-slate-700'
                    }`}
                  >
                    <span>{viewLabels[viewKey]}</span>
                    {activeView === viewKey && <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Center: Command Palette Trigger */}
        <div className="flex-1 max-w-md mx-2 hidden lg:block">
          <button
            onClick={onOpenCommandPalette}
            className="w-full flex items-center justify-between text-xs px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200/60 border border-slate-200 text-slate-500 transition-colors shadow-inner"
          >
            <span className="flex items-center gap-2">
              <Search className="w-3.5 h-3.5 text-slate-400" />
              <span>Search stations, incidents, parameter rules...</span>
            </span>
            <kbd className="flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white text-[10px] font-mono text-slate-500 border border-slate-300 shadow-xs">
              <Command className="w-2.5 h-2.5" /> K
            </kbd>
          </button>
        </div>

        {/* Right: Controls, Toggles, Status */}
        <div className="flex items-center gap-2.5">
          {/* Mobile search trigger */}
          <button
            onClick={onOpenCommandPalette}
            className="lg:hidden p-1.5 rounded-lg bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200"
            title="Search"
          >
            <Search className="w-4 h-4" />
          </button>

          {/* UTC / IST Toggle */}
          <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg p-0.5 text-xs font-mono">
            <button
              onClick={() => setTimeMode('UTC')}
              className={`px-2 py-0.5 rounded transition-all ${
                timeMode === 'UTC' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Coordinated Universal Time"
            >
              UTC
            </button>
            <button
              onClick={() => setTimeMode('IST')}
              className={`px-2 py-0.5 rounded transition-all ${
                timeMode === 'IST' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Indian Standard Time (UTC+5:30)"
            >
              IST
            </button>
          </div>

          {/* Inference Engine Status Indicator with live breathing pulse */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-[11px] font-mono shadow-xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600" />
            </span>
            <span className="text-emerald-900 font-semibold">Observation service:</span>
            <span className="text-emerald-700 font-bold">
              {engineStatus}
            </span>
          </div>

          {/* Help / About Dialog Trigger */}
          <button
            onClick={() => setAboutModalOpen(true)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-slate-100 transition-colors"
            title="Scientific Contract & Architecture"
          >
            <HelpCircle className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* About Modal in Clean White Styling */}
      {aboutModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="max-w-lg w-full bg-white border border-slate-200 rounded-2xl p-6 shadow-2xl text-slate-800">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-slate-900 text-base">SkyGuard AI · Scientific Contract</h3>
              </div>
              <button 
                onClick={() => setAboutModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-lg font-mono"
              >
                ✕
              </button>
            </div>
            <div className="mt-4 space-y-3 text-xs leading-relaxed text-slate-600">
              <p>
                <strong className="text-blue-700">SIH Problem Statement 26073:</strong> Intelligent real-time anomaly detection and quality control for Automatic Weather Stations.
              </p>
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 font-mono text-[11px] space-y-1">
                <div className="text-blue-700 font-bold">Strict Three-Parameter Physical Inputs:</div>
                <div className="text-slate-700">1. Air Temperature (°C)</div>
                <div className="text-slate-700">2. Station Pressure (hPa)</div>
                <div className="text-slate-700">3. Relative Humidity (%)</div>
              </div>
              <p>
                Operational screening combines pressure-aware physical checks, causal rolling statistics, frozen-value and rate checks, and time-aligned spatial buddies. The verified offline Phase 10 detector uses interpretable tabular models; its neural TCN remains advisory because it did not satisfy every unseen-station false-alarm constraint.
              </p>
              <p className="text-slate-500 text-[11px]">
                Live Indian hardware fault labels are not available. Operational values are therefore labelled as evidence scores, while accuracy figures are shown only inside the explicitly marked fault-injected offline benchmark.
              </p>
              {lastObservationUtc && <p className="text-[11px] text-slate-500">Latest stored observation: {lastObservationUtc}</p>}
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setAboutModalOpen(false)}
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs transition-colors shadow-sm shadow-blue-500/30"
              >
                Close & Return
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
