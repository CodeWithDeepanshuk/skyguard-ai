'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { WorkingViewFilter, StationObservation } from '@/lib/types';

interface OperationalContextType {
  timeMode: 'UTC' | 'IST';
  setTimeMode: (mode: 'UTC' | 'IST') => void;
  activeView: WorkingViewFilter;
  setActiveView: (view: WorkingViewFilter) => void;
  selectedStation: StationObservation | null;
  setSelectedStation: (station: StationObservation | null) => void;
  isDrawerOpen: boolean;
  setIsDrawerOpen: (open: boolean) => void;
  isCommandPaletteOpen: boolean;
  setIsCommandPaletteOpen: (open: boolean) => void;
}

const OperationalContext = createContext<OperationalContextType | undefined>(undefined);

export function OperationalProvider({ children }: { children: React.ReactNode }) {
  const [timeMode, setTimeMode] = useState<'UTC' | 'IST'>('UTC');
  const [activeView, setActiveView] = useState<WorkingViewFilter>('ALL_INDIA');
  const [selectedStation, setSelectedStation] = useState<StationObservation | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);

  // Sync station selection with drawer state
  const handleSetSelectedStation = (station: StationObservation | null) => {
    setSelectedStation(station);
    setIsDrawerOpen(!!station);
  };

  return (
    <OperationalContext.Provider
      value={{
        timeMode,
        setTimeMode,
        activeView,
        setActiveView,
        selectedStation,
        setSelectedStation: handleSetSelectedStation,
        isDrawerOpen,
        setIsDrawerOpen,
        isCommandPaletteOpen,
        setIsCommandPaletteOpen,
      }}
    >
      {children}
    </OperationalContext.Provider>
  );
}

export function useOperational() {
  const context = useContext(OperationalContext);
  if (!context) {
    throw new Error('useOperational must be used within an OperationalProvider');
  }
  return context;
}
