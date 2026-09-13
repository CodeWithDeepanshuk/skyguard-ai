'use client';

import { useEffect, useState } from 'react';

type EngineState = 'checking' | 'connected' | 'waking';

export default function ServiceStatus() {
  const [engineState, setEngineState] = useState<EngineState>('checking');

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;

    const check = async () => {
      attempt += 1;
      try {
        const response = await fetch('/api/health', { cache: 'no-store' });
        const data = await response.json();
        if (cancelled) return;
        if (response.ok && data.ml_service === true) {
          setEngineState('connected');
          return;
        }
      } catch {
        // The next bounded retry handles Render free-tier cold starts.
      }

      if (cancelled) return;
      setEngineState('waking');
      if (attempt < 7) timer = setTimeout(check, 5000);
    };

    void check();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  const connected = engineState === 'connected';
  const checking = engineState === 'checking';
  const label = connected ? 'Live Engine Connected' : checking ? 'Checking Engine' : 'Engine Waking · Auto Retry';

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-center space-x-2 rounded-full border px-3 py-1.5 text-[11px] font-bold tracking-wide shadow-[0_0_24px_rgba(52,211,153,0.08)] ${
        connected
          ? 'border-emerald-300/25 bg-emerald-400/[0.07] text-emerald-300'
          : 'border-amber-300/25 bg-amber-400/[0.07] text-amber-200'
      }`}
    >
      <span className="relative flex h-2 w-2">
        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-70 ${connected ? 'bg-emerald-400' : 'bg-amber-300'}`} />
        <span className={`relative inline-flex h-2 w-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
      </span>
      <span className="hidden sm:inline">{label}</span>
      <span className="sm:hidden">{connected ? 'Online' : checking ? 'Checking' : 'Waking'}</span>
    </div>
  );
}
