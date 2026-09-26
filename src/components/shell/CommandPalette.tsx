'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Activity, 
  BarChart3, 
  BrainCircuit, 
  Command, 
  Database, 
  FlaskConical, 
  RadioTower, 
  Search, 
  ShieldAlert, 
  ShieldCheck 
} from 'lucide-react';
import { StationObservation } from '@/lib/types';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  stations?: StationObservation[];
  onSelectStation?: (station: StationObservation) => void;
}

export function CommandPalette({ isOpen, onClose, stations = [], onSelectStation }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        isOpen ? onClose() : undefined;
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const quickLinks = [
    { name: 'National Command Centre', href: '/', icon: RadioTower, desc: 'Live India AWS map and active intelligence' },
    { name: 'AWS Network Table & Map', href: '/stations', icon: RadioTower, desc: 'Browse all 1,153 catalog stations' },
    { name: 'Incident Command & Persistence', href: '/incidents', icon: Activity, desc: 'Investigate confirmed anomaly episodes' },
    { name: 'Scientific Analytics & Ablation', href: '/analytics', icon: BarChart3, desc: 'Precision, recall, holdouts & ablation ladder' },
    { name: 'Scientific Evidence Matrix', href: '/validation', icon: ShieldCheck, desc: 'Audited empirical metrics and verification reports' },
    { name: 'Jury Demonstration Sandbox', href: '/jury-demo', icon: FlaskConical, desc: 'Interactive controlled fault injection & concentric spatial consensus demo' },
    { name: 'Data Sources & Provenance', href: '/data-sources', icon: Database, desc: 'Multi-provider ingestion pipeline' },
    { name: 'Model Architecture & Graph', href: '/model', icon: BrainCircuit, desc: '3-parameter TCN, Spatial QC, and Specialists' },
  ];

  const filteredStations = query.trim()
    ? stations.filter(
        (s) =>
          s.station_name.toLowerCase().includes(query.toLowerCase()) ||
          s.station_id.toLowerCase().includes(query.toLowerCase()) ||
          (s.state && s.state.toLowerCase().includes(query.toLowerCase()))
      ).slice(0, 8)
    : [];

  const filteredLinks = query.trim()
    ? quickLinks.filter(
        (l) =>
          l.name.toLowerCase().includes(query.toLowerCase()) ||
          l.desc.toLowerCase().includes(query.toLowerCase())
      )
    : quickLinks;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-slate-950/40 backdrop-blur-xs">
      <div 
        className="w-full max-w-xl bg-white border border-slate-200 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[75vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-200 bg-slate-50/75">
          <Search className="w-4 h-4 text-blue-600 flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search stations by name or ID, or navigate pages..."
            className="flex-1 bg-transparent text-sm text-slate-900 placeholder-slate-400 focus:outline-none"
          />
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-600 border border-slate-300">
            ESC
          </kbd>
        </div>

        {/* Results Container */}
        <div className="flex-1 overflow-y-auto p-2 space-y-4 text-xs">
          {/* Station Results */}
          {filteredStations.length > 0 && (
            <div>
              <div className="px-3 py-1 text-[10px] uppercase font-mono font-semibold tracking-wider text-blue-700">
                Stations ({filteredStations.length})
              </div>
              <div className="space-y-0.5 mt-1">
                {filteredStations.map((station) => (
                  <button
                    key={station.station_id}
                    onClick={() => {
                      if (onSelectStation) onSelectStation(station);
                      onClose();
                    }}
                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-blue-50 text-left transition-colors group"
                  >
                    <div>
                      <div className="font-semibold text-slate-800 group-hover:text-blue-700">
                        {station.station_name}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        ID: {station.station_id} {station.state ? `· ${station.state}` : ''}
                      </div>
                    </div>
                    <span className="text-[10px] font-mono text-blue-600 group-hover:underline">
                      View on Map →
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Quick Links */}
          {filteredLinks.length > 0 && (
            <div>
              <div className="px-3 py-1 text-[10px] uppercase font-mono font-semibold tracking-wider text-slate-500">
                Navigation & Systems
              </div>
              <div className="space-y-0.5 mt-1">
                {filteredLinks.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.href}
                      onClick={() => {
                        router.push(item.href);
                        onClose();
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-100 text-left transition-colors group"
                    >
                      <Icon className="w-4 h-4 text-slate-500 group-hover:text-blue-600 flex-shrink-0" />
                      <div>
                        <div className="font-semibold text-slate-800 group-hover:text-blue-700">
                          {item.name}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {item.desc}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {query.trim() && filteredStations.length === 0 && filteredLinks.length === 0 && (
            <div className="p-8 text-center text-slate-500 text-xs">
              No matching stations or navigation items found for &ldquo;{query}&rdquo;.
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 text-[10px] font-mono text-slate-500 flex items-center justify-between">
          <span>SkyGuard AI Master Command Palette</span>
          <span>1,008 Indian AWS Stations Indexed</span>
        </div>
      </div>
    </div>
  );
}
