# SkyGuard AI — Scientific Design System & Interface Specification
**Document ID:** `docs/SKYGUARD_DESIGN_SYSTEM.md`  
**Author:** Principal Product Designer & Senior Frontend Architect  
**Project:** SkyGuard AI · SIH Problem Statement 26073  
**Status:** PRODUCTION SPECIFICATION  

---

## 1. Design Philosophy & Operational Principles

SkyGuard AI is India's national Automatic Weather Station (AWS) sensor-quality command platform. Its design philosophy targets the mission-critical credibility of world-class operational meteorological command systems (such as Tomorrow.io, aviation flight operations centres, and satellite mission control) without copying proprietary assets, fonts, or code.

### Core Product Principles
1. **Map First**: Geospatial context is the dominant canvas. Over 70% of the flagship viewport presents the live Indian subcontinent with real-time station vertices.
2. **Location First**: Observations and faults are anchored in explicit physical geography, elevation MSL, and spatial neighbour clusters.
3. **Time First**: Every telemetry point displays explicit UTC and IST timestamps and data freshness ages. Time travel across historical trajectories is driven by a non-hallucinating time scrubber.
4. **Operational Impact First**: Sensor anomalies are ranked by confidence, persistence duration, and severity rather than raw anomaly scores.
5. **Actionable Intelligence**: Every alert is paired with an attributed physical failure class (e.g., spike, freeze, slow drift, communication drop).
6. **Low Cognitive Load & Progressive Disclosure**: Low zoom clusters stations into regional density indicators; regional zoom reveals individual status glyphs; high zoom surfaces geodesic buddy vectors. Clicking any station opens an in-context slide-over drawer without page navigation.
7. **Scientific Truth**: If data is missing or delayed, the UI explicitly shows `"No live observation available"` or `"Catalog Unverified"` rather than fabricating believable numbers.

---

## 2. Color Palette & Atmospheric Lighting

The design system employs a curated, deep meteorological palette with high contrast, calm backgrounds, and clear semantic states that meet WCAG AA standards.

| Token | Hex / Value | Operational Usage |
|---|---|---|
| `--bg-deep` | `#050c16` | Deep meteorological void, canvas base, outer margins |
| `--bg-surface` | `#081626` | Primary application shell, top bar, sidebar background |
| `--bg-panel` | `#0c2234` | Elevated command cards, station drawers, legend containers |
| `--bg-raised` | `#0f2b44` | Active card state, focused list rows |
| `--border-subtle` | `rgba(56, 189, 248, 0.12)` | Card outlines, dividers, timeline ticks |
| `--border-default`| `rgba(56, 189, 248, 0.22)` | Primary interactive borders, input fields |
| `--accent-cyan` | `#38bdf8` | Primary brand accent, active tabs, selected markers |
| `--accent-sky` | `#0284c7` | Secondary accents, progress indicators |
| `--text-primary` | `#f8fafc` | Main headings, observed sensor readings, primary labels |
| `--text-muted` | `#94a3b8` | Metadata descriptions, units, secondary labels |
| `--text-dim` | `#64748b` | Timestamps, coordinates, breadcrumbs |

### Semantic Sensor & Health Status Scale
To avoid relying solely on color (WCAG AA accessibility), every operational state couples a tailored color with a distinctive geometric icon and shape glyph:

| Quality State | Color Hex | Glyph / Shape | Meaning & Criteria |
|---|---|---|---|
| **Healthy / Coherent** | `#10b981` (Emerald) | Solid Circle | Coherent with diurnal cycle and buddy stations ($\Delta T \le 1.8^\circ\text{C}$) |
| **Watch** | `#f59e0b` (Amber) | Rotated Diamond (45°) | Minor dwell, low-magnitude trend divergence under investigation |
| **Probable Fault** | `#f97316` (Orange) | Rounded Square | Divergence exceeding 99th percentile, pending persistence gate |
| **Critical Anomaly** | `#ef4444` (Rose) | Equilateral Triangle | Confirmed persistent hardware failure ($k=3$ in $n=5$) |
| **Multi-Sensor Anomaly**| `#a855f7` (Purple) | Pulsing Hexagon | Simultaneous uncorrelated failure across $T, P, \text{RH}$ |
| **Stale / Offline** | `#64748b` (Slate) | Dimmed Ring | Telemetry age $> 3$ hours; no active transmission |
| **Catalog Unverified**| `#3b82f6` (Blue) | Dashed Ring | Registered in metadata catalog without live telemetry ingest |

---

## 3. Typography Hierarchy

The typography pairs a clean modern humanist sans-serif for high readability with an engineering monospace for numeric data:

- **Primary UI Text**: `Inter`, `-apple-system`, `sans-serif`.
  * Weights: 400 (regular), 500 (medium), 600 (semibold), 700 (bold), 800 (extrabold).
  * Used for: Titles, button labels, descriptions, and briefings.
- **Scientific Monospace**: `JetBrains Mono`, `ui-monospace`, `monospace`.
  * Weights: 400, 600, 700.
  * Used strictly for: Station IDs, coordinates, elevation, observation values ($38.7^\circ\text{C}$), Z-scores, residuals, timestamps, and model hashes.

---

## 4. Spacing, Elevation & Layout Density

- **Operational Density Scale**: 4px, 8px, 12px, 16px, 24px, 32px.
- **Border Radius**: 8px (`rounded-lg`) for buttons and small badges; 12px (`rounded-xl`) for panels and drawers. No oversized 24px+ mobile-app radiuses.
- **Elevation**: 1px subtle desaturated border (`rgba(56, 189, 248, 0.22)`) with clean directional box-shadows (`shadow-xl shadow-black/40`). Zero exaggerated neon glows or fluorescent borders.

---

## 5. Reusable Component Inventory

1. **`AppShell`**: Coordinates top bar, collapsible sidebar, status bar, and command palette.
2. **`TopBar`**: Contains SkyGuard crest, working view filter, global search trigger, UTC/IST toggle, and inference engine status indicator.
3. **`Sidebar`**: Collapsible left navigation (expanded: 240px, collapsed: 64px) with keyboard accessibility and tooltips.
4. **`StatusBar`**: High-density operational KPI strip displaying real station counts, reporting stations, health breakdown, and data age.
5. **`LiveMap`**: MapLibre GL JS vector/raster canvas with low-zoom clustering, dynamic layer coloring, and geodesic neighbour lines.
6. **`MapLegend`**: Dynamic legend automatically adapting to active layer (Temperature, Pressure, RH, Anomaly Probability, Spatial Residual).
7. **`TimeScrubber`**: Bottom timeline player supporting Past 24h, 12h, 6h, and Live with dual UTC/IST timestamp formatting.
8. **`StationDrawer`**: Slide-over drawer displaying station profile, $T/P/\text{RH}$ metric cards, "Why Flagged" explainability, and 3-track causal charts.
9. **`NeighbourConsensus`**: Inverse-distance weighted consensus table displaying distance in km and individual station readings.
10. **`WeatherVsFaultCard`**: Visual demonstration contrasting an isolated hardware spike against a spatially coherent frontal storm.
11. **`CommandPalette`**: Global `Ctrl/Cmd + K` search modal indexing 543 stations, active incidents, and system routes.
