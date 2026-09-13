# SkyGuard AI — Frontend Architecture & Technical Implementation
**Document ID:** `docs/UI_ARCHITECTURE.md`  
**Author:** Senior Frontend Architect & Principal Product Designer  
**Project:** SkyGuard AI · SIH Problem Statement 26073  
**Status:** ARCHITECTURAL SPECIFICATION  

---

## 1. Technical Stack Overview

```
Frontend Runtime:       Next.js 14.2.35 (React 18.3.1)
Language:               TypeScript 5.6.3 (Strict mode)
Styling Engine:         Tailwind CSS 3.4.14 with PostCSS 8
Geospatial Engine:      MapLibre GL JS (WebGL vector / raster canvas)
Charting Library:       Recharts 2.13.3 (Crosshair synchronized multi-track time series)
Iconography:            Lucide React 0.454.0
State Management:       React Context (OperationalContext) for global viewport/time state
Server Architecture:    Next.js App Router serverless edge proxies with FastAPI Python backend
Deployment Targets:     Vercel (Frontend & Serverless APIs) + Render (ML Backend & Ingestion)
```

---

## 2. Directory & Component Hierarchy

```
src/
├── app/
│   ├── layout.tsx                # Root layout with OperationalProvider, AppShell, fonts & MapLibre CSS
│   ├── page.tsx                  # Page 1: National Command Centre (70% Map + 30% Intelligence)
│   ├── stations/page.tsx         # Page 2: AWS Network (Map + Table Dual View + Faceted Filters)
│   ├── stations/[id]/page.tsx    # Single station deep-linkable dossier
│   ├── incidents/page.tsx        # Page 3: Incident Command (Master Feed + Persistence Timeline)
│   ├── analytics/page.tsx        # Page 4: Scientific Analytics Workspace (A0-A7 Ladder + Multi-Seed)
│   ├── validation/page.tsx       # Page 5: 25-Gate Operational Matrix (Grouped 5x5 Cards + Drawer)
│   ├── data-sources/page.tsx     # Page 6: Data Sources & Provenance Pipeline
│   ├── model/page.tsx            # Page 7: Model Architecture Graph & 3-Parameter Engine
│   ├── system/page.tsx           # Page 8: Real-Time System Health & Diagnostic Telemetry
│   └── api/                      # Serverless routes & proxies to Python backend
├── components/
│   ├── shell/                    # AppShell, TopBar, Sidebar, StatusBar, CommandPalette
│   ├── map/                      # LiveMap, MapToolbar, MapLegend, TimeScrubber
│   ├── station/                  # StationDrawer, StationHeader, SensorMetricCard, SensorTrendChart,
│   │                             # NeighbourConsensus, ExplainabilityCard, WeatherVsFaultCard,
│   │                             # LiveIntelligencePanel
│   └── common/                   # QualityBadge, SeverityBadge, Tooltip, Skeleton
├── context/
│   └── OperationalContext.tsx    # Shared timeMode, activeView, selectedStation, drawer state
├── lib/
│   ├── types.ts                  # Core domain TypeScript interfaces
│   ├── designTokens.ts           # Color tokens, status scales, typography, map settings
│   ├── formatters.ts             # Timezone-aware formatters (UTC/IST), numbers, residuals
│   └── geo.ts                    # Haversine geodesy formula, neighbour search, regional bounds
└── docs/                         # Specifications & audit documentation
```

---

## 3. Geospatial Architecture: MapLibre GL JS

### Dynamic Client-Side Loading
MapLibre GL JS relies on browser WebGL rendering (`window`, `navigator`, `HTMLCanvasElement`). To prevent Server-Side Rendering (SSR) hydration mismatch, `LiveMap` is imported dynamically:
```tsx
const LiveMap = dynamic(() => import('@/components/map/LiveMap'), {
  ssr: false,
  loading: () => <MapSkeleton />,
});
```

### Tile Source & Basemap
The map uses CARTO Dark Matter vector/raster tiles:
`https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png`
which requires **zero paid tokens or third-party license restrictions**.

### Performance & Scalability
- **GeoJSON Source & Clustering**: 543 Indian stations are loaded as a single GeoJSON `FeatureCollection`.
- Low-zoom levels ($z < 7$) cluster nearby stations into density circles, preventing DOM clutter.
- Regional and station zoom ($z \ge 7$) render individual unclustered glyphs with custom shape and color styling matching the active meteorological layer.
- Subcontinent SVG fallback is embedded in the component in case WebGL context is unavailable.

---

## 4. State Management & URL Synchronization

1. **`OperationalContext`**:
   - `timeMode`: `'UTC'` | `'IST'` (toggles all displayed timestamps across every page).
   - `activeView`: `ALL_INDIA`, `NORTH_INDIA`, `SOUTH_INDIA`, `EAST_INDIA`, `WEST_CENTRAL`, `CRITICAL_STATIONS`, `ACTIVE_INCIDENTS`, `HOLDOUT_SET`.
   - `selectedStation`: Currently inspected station object.
   - `isDrawerOpen`: Controls right-side slide-over drawer visibility.
   - `isCommandPaletteOpen`: Global `Ctrl/Cmd + K` search dialog trigger.
2. **Persistence Timeline State Machine**:
   - Illustrates the causal persistence gate ($k=3$ votes in rolling window $n=5$) that eliminates false alarms from noisy packets.
