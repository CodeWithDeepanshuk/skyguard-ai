import React from 'react';

export function CardSkeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-white border border-slate-200 rounded-xl p-4 shadow-sm ${className}`}>
      <div className="h-4 bg-slate-200 rounded w-1/3 mb-3"></div>
      <div className="h-8 bg-slate-100 rounded w-2/3 mb-2"></div>
      <div className="h-3 bg-slate-100 rounded w-1/2"></div>
    </div>
  );
}

export function MapSkeleton() {
  return (
    <div className="w-full h-full min-h-[500px] bg-slate-100 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-slate-100 to-slate-200 animate-pulse" />
      <div className="relative z-10 flex flex-col items-center text-center">
        <div className="w-12 h-12 rounded-full border-3 border-blue-600/30 border-t-blue-600 animate-spin mb-4" />
        <p className="text-sm font-bold text-slate-800">Initializing National Geospatial Canvas...</p>
        <p className="text-xs text-slate-500 font-mono mt-1">CARTO Positron · 1,008 Station Vertices</p>
      </div>
    </div>
  );
}

export function TableRowSkeleton({ cols = 6 }: { cols?: number }) {
  return (
    <tr className="animate-pulse border-b border-slate-100">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-4">
          <div className="h-4 bg-slate-200/70 rounded w-3/4"></div>
        </td>
      ))}
    </tr>
  );
}
