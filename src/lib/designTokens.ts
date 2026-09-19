/**
 * SkyGuard AI - Scientific Design System Tokens (Light Operational Command Theme)
 * Pure White Canvas, Deep Slate Navy Typography, Classic Meteorological Colors & Smooth Animations
 */

export const SKYGUARD_TOKENS = {
  colors: {
    bg: {
      deep: '#f8fafc',         // Pristine chalk slate canvas
      surface: '#ffffff',      // Pure white surface
      panel: '#ffffff',        // Elevated panel
      card: '#ffffff',         // Card surface
      hover: '#f1f5f9',        // Interactive hover
      overlay: 'rgba(15, 23, 42, 0.4)',
    },
    border: {
      subtle: 'rgba(15, 23, 42, 0.08)',
      default: 'rgba(15, 23, 42, 0.14)',
      focus: '#2563eb',
      active: '#1d4ed8',
    },
    text: {
      primary: '#0f172a',      // Deep slate navy
      secondary: '#475569',    // Slate charcoal
      muted: '#64748b',        // Slate muted
      inverse: '#ffffff',
    },
    accent: {
      blue: '#2563eb',         // Royal Cobalt
      cobalt: '#1d4ed8',
      cyan: '#0284c7',         // Ice Cyan
      emerald: '#059669',      // Alpine Emerald
      amber: '#d97706',        // Warm Ochre Amber
      crimson: '#dc2626',      // Crimson Ruby
      violet: '#7c3aed',       // Amethyst Violet
    },
    status: {
      healthy: {
        bg: '#ecfdf5',
        border: '#a7f3d0',
        text: '#065f46',
        hex: '#059669',
        label: 'Healthy / Coherent',
      },
      watch: {
        bg: '#fffbeb',
        border: '#fde68a',
        text: '#92400e',
        hex: '#d97706',
        label: 'Watch',
      },
      probable_fault: {
        bg: '#fff7ed',
        border: '#fed7aa',
        text: '#9a3412',
        hex: '#ea580c',
        label: 'Probable Fault',
      },
      critical: {
        bg: '#fef2f2',
        border: '#fecaca',
        text: '#991b1b',
        hex: '#dc2626',
        label: 'Critical Anomaly',
      },
      multi_sensor: {
        bg: '#faf5ff',
        border: '#e9d5ff',
        text: '#6b21a8',
        hex: '#7c3aed',
        label: 'Multi-Sensor Failure',
      },
      stale: {
        bg: '#f8fafc',
        border: '#e2e8f0',
        text: '#64748b',
        hex: '#64748b',
        label: 'Stale / Offline',
      },
      unverified: {
        bg: '#f0f9ff',
        border: '#bae6fd',
        text: '#0369a1',
        hex: '#0284c7',
        label: 'Catalog Unverified',
      },
    }
  },
  typography: {
    fontFamily: {
      sans: 'Inter, system-ui, sans-serif',
      mono: 'JetBrains Mono, ui-monospace, SFMono-Regular, monospace',
    }
  },
  map: {
    defaultCenter: [78.9629, 22.5937] as [number, number], // Geographic center of India
    defaultZoom: 4.6,
    minZoom: 3.5,
    maxZoom: 16,
    // Authenticated CARTO basemaps with valid API key for watermark-free rendering
    cartoApiKey: process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9',
    // Genuine, rich geographic/physical Earth basemap (CARTO Voyager)
    cartoVoyagerRasterUrls: [
      `https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
      `https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
      `https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
      `https://d.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
    ],
    // Clean light basemap (CARTO Positron)
    cartoLightRasterUrls: [
      `https://a.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
      `https://b.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
      `https://c.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
      `https://d.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
    ],
    cartoLightRasterUrl: `https://a.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
    cartoLightStyle: `https://basemaps.cartocdn.com/gl/positron-gl-style/style.json?key=${process.env.NEXT_PUBLIC_CARTO_API_KEY || 'cb1_3j1r_1_be62fb6db7be11a13ab5c0a9'}`,
    // India specific framing bounds [southwest, northeast]
    indiaBounds: [
      [68.0, 7.0],   // Southwest: Gujarat / Indian Ocean / Kanyakumari
      [97.5, 36.5],  // Northeast: Arunachal Pradesh / Ladakh
    ] as [[number, number], [number, number]],
    indiaCenter: [79.2, 21.8] as [number, number],
  }
};
