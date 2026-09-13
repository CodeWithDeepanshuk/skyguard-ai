'use client';

import React, { useEffect, useRef, useState } from 'react';

/** Lightweight, original meteorological motion layer (CSS + SVG only). */
export function AtmosphereBackground() {
  const root = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const visibility = () => setPaused(document.hidden);
    const pointer = (event: PointerEvent) => {
      if (!root.current) return;
      root.current.style.setProperty('--atmo-x', `${(event.clientX / window.innerWidth - 0.5) * 14}px`);
      root.current.style.setProperty('--atmo-y', `${(event.clientY / window.innerHeight - 0.5) * 10}px`);
    };
    document.addEventListener('visibilitychange', visibility);
    window.addEventListener('pointermove', pointer, { passive: true });
    visibility();
    return () => {
      document.removeEventListener('visibilitychange', visibility);
      window.removeEventListener('pointermove', pointer);
    };
  }, []);

  return (
    <div ref={root} className="atmosphere" data-paused={paused ? 'true' : 'false'} aria-hidden="true">
      <div className="atmosphere__aurora atmosphere__aurora--one" />
      <div className="atmosphere__aurora atmosphere__aurora--two" />
      <div className="atmosphere__ribbon atmosphere__ribbon--one" />
      <div className="atmosphere__ribbon atmosphere__ribbon--two" />
      <svg className="atmosphere__isobars" viewBox="0 0 1200 700" preserveAspectRatio="none">
        <path d="M-80 180 C170 30 310 320 560 165 S930 30 1280 210" />
        <path d="M-100 255 C170 105 350 390 600 235 S980 105 1300 275" />
        <path d="M-80 505 C210 315 350 650 665 455 S1010 350 1280 510" />
        <path d="M120 740 C250 500 520 520 690 690 S1020 670 1150 470" />
      </svg>
      <span className="atmosphere__wave atmosphere__wave--one" />
      <span className="atmosphere__wave atmosphere__wave--two" />
    </div>
  );
}
