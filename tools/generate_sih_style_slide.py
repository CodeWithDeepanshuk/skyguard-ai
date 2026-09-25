"""
Generate Technical Approach Slide matching the reference presentation style:
- Header: Oval Team Badge | 'TECHNICAL APPROACH' | Smart India Hackathon Logo
- Left (41%): Dashed blue container with red bold bullet points & verified tech stack
- Right (59%): Rich architectural diagram with yellow connector lines, exact node anchors, icons, and PostgreSQL badge
- Output: HTML, High-Res PNG (1920x1080), and PPTX (16:9)
"""

import os
import subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_HTML = r"c:\Users\deepa\OneDrive\Desktop\Sih 73\sih73_technical_approach_reference_style.html"
OUTPUT_PNG = r"c:\Users\deepa\OneDrive\Desktop\Sih 73\sih73_technical_approach_reference_style.png"
OUTPUT_PPTX = r"c:\Users\deepa\OneDrive\Desktop\Sih 73\sih73_technical_approach_reference_style.pptx"

def create_html():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Technical Approach - SkyGuard AI - SIH 2024</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1920px;
    height: 1080px;
    background: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #1e293b;
    position: relative;
    overflow: hidden;
    padding: 16px 24px;
  }

  /* Outer Slide Frame like Reference */
  .slide-border {
    position: absolute;
    top: 8px; left: 8px; right: 8px; bottom: 8px;
    border: 3.5px solid #1e293b;
    pointer-events: none;
    z-index: 100;
  }

  /* Header Bar */
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 75px;
    padding: 0 16px;
    border-bottom: 2px solid #cbd5e1;
    margin-bottom: 16px;
  }

  .team-badge {
    border: 3px solid #2563eb;
    border-radius: 9999px;
    padding: 6px 28px;
    font-size: 24px;
    font-weight: 800;
    color: #1d4ed8;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .slide-title {
    font-size: 46px;
    font-weight: 900;
    font-family: 'Times New Roman', Georgia, serif;
    color: #1a2a5a;
    letter-spacing: 3px;
    text-align: center;
  }

  .sih-logo-block {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .sih-text {
    text-align: right;
    font-weight: 900;
    font-size: 16px;
    line-height: 1.15;
    color: #0f172a;
    letter-spacing: 0.5px;
  }

  .sih-year {
    font-size: 20px;
    color: #0f172a;
    font-weight: 900;
  }

  /* Main Split Layout */
  .main-container {
    display: flex;
    height: calc(1080px - 125px);
    gap: 20px;
  }

  /* Left Column: Dashed Container */
  .left-column {
    flex: 0 0 760px;
    border: 2.5px dashed #2563eb;
    border-radius: 10px;
    padding: 18px 22px;
    background: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .tech-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 14.2px;
    line-height: 1.34;
    color: #1e293b;
  }

  .bullet-icon {
    color: #dc2626;
    font-size: 15px;
    font-weight: bold;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .tech-highlight {
    font-weight: 800;
    color: #dc2626;
  }

  /* Right Column: Architectural Diagram */
  .right-column {
    flex: 1;
    position: relative;
    background: #ffffff;
    border-radius: 10px;
    height: 100%;
  }

  /* Connector SVG Canvas with exact 1:1 pixel coords */
  .connector-canvas {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    z-index: 1;
    pointer-events: none;
  }

  /* Diagram Node Box */
  .diagram-node {
    position: absolute;
    z-index: 2;
    background: #ffffff;
    border: 2px solid #eab308;
    border-radius: 8px;
    padding: 6px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
  }

  .node-title {
    font-size: 13.5px;
    font-weight: 700;
    color: #1e293b;
    line-height: 1.2;
  }

  .node-sub {
    font-size: 11px;
    color: #64748b;
    font-weight: 500;
  }

  .node-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  /* Central FastAPI Backend */
  #node-backend {
    top: 200px; left: 240px; width: 220px; height: 80px;
    border: 2.5px solid #ef4444; background: #fef2f2;
    padding: 10px 14px;
    border-radius: 10px;
  }

  /* Ingest & Cache */
  #node-ingest {
    top: 25px; left: 245px; width: 210px; height: 60px;
    border-color: #3b82f6; background: #eff6ff;
  }

  #node-sqlite {
    top: 120px; left: 30px; width: 190px; height: 60px;
    border-color: #64748b; background: #f8fafc;
  }

  /* Frontend Clients */
  #node-web {
    top: 320px; left: 30px; width: 190px; height: 65px;
    border-color: #0284c7; background: #f0f9ff;
  }

  #node-map {
    top: 460px; left: 20px; width: 165px; height: 60px;
    border-color: #059669; background: #f0fdf4;
  }

  #node-charts {
    top: 460px; left: 205px; width: 165px; height: 60px;
    border-color: #f59e0b; background: #fffbeb;
  }

  /* Right Microservices Stack (Left = 560px, Width = 370px, Height = 56px) */
  .right-stack-node {
    left: 560px; width: 370px; height: 56px;
  }
  #node-range-qc { top: 20px; border-color: #6366f1; }
  #node-cusum    { top: 95px; border-color: #eab308; }
  #node-lightgbm { top: 170px; border-color: #8b5cf6; }
  #node-spatial  { top: 245px; border-color: #0ea5e9; }
  #node-triage   { top: 320px; border-color: #10b981; background: #ecfdf5; }
  #node-impute   { top: 395px; border-color: #06b6d4; }
  #node-alerts   { top: 470px; border-color: #f97316; background: #fff7ed; }
  #node-postgres { top: 545px; border-color: #2563eb; background: #eff6ff; }
  #node-archive  { top: 620px; border-color: #64748b; background: #f8fafc; }

  /* Big Postgres Elephant Logo on Right Margin */
  .postgres-badge {
    position: absolute;
    left: 955px;
    top: 535px;
    width: 85px;
    height: 85px;
    z-index: 3;
  }
</style>
</head>
<body>

<div class="slide-border"></div>

<div class="header">
  <div class="team-badge">Team SkyGuard</div>
  <div class="slide-title">TECHNICAL APPROACH</div>
  <div class="sih-logo-block">
    <svg width="48" height="48" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="46" fill="none" stroke="#f97316" stroke-width="4"/>
      <path d="M50 18 C34 18 22 30 22 46 C22 56 28 65 37 70 L37 78 L63 78 L63 70 C72 65 78 56 78 46 C78 30 66 18 50 18 Z" fill="#eff6ff" stroke="#3b82f6" stroke-width="3"/>
      <path d="M42 78 L58 78 M45 84 L55 84" stroke="#10b981" stroke-width="4" stroke-linecap="round"/>
      <circle cx="38" cy="38" r="4" fill="#ef4444"/>
      <circle cx="62" cy="38" r="4" fill="#10b981"/>
      <circle cx="50" cy="50" r="5" fill="#f59e0b"/>
      <line x1="38" y1="38" x2="50" y2="50" stroke="#94a3b8" stroke-width="2"/>
      <line x1="62" y1="38" x2="50" y2="50" stroke="#94a3b8" stroke-width="2"/>
      <line x1="50" y1="50" x2="50" y2="70" stroke="#94a3b8" stroke-width="2"/>
    </svg>
    <div class="sih-text">
      SMART INDIA<br>HACKATHON<br><span class="sih-year">2024</span>
    </div>
  </div>
</div>

<div class="main-container">
  <!-- LEFT COLUMN -->
  <div class="left-column">
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Frontend</span> Next.js 14 for reactive operator web app and React 18 for component state management.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">MapLibre GL</span> for interactive geospatial mapping of weather stations with color-coded health badges.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Recharts</span> for real-time diurnal trend curves across temperature, pressure, and relative humidity.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">FastAPI & Python 3.12</span> as a high-performance, asynchronous REST backend framework for streaming telemetry.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">PostgreSQL</span> for relational observation management, and <span class="tech-highlight">SQLite</span> for fast local caching and edge replay.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">LightGBM & Scikit-learn</span> GBDT and Isolation Forest models for multivariate anomaly scoring.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">CUSUM Algorithm</span> for continuous cumulative tracking of slow calibration drift and persistent offset.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Range & Step QC</span> WMO-standard physical limit checks and sudden rate-of-change jump detection.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Spatial Consensus Engine</span> Cross-station correlation using peer stations with elevation and distance weighting.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Decision Triage</span> Classifies events into Likely Weather, Suspected Sensor Fault, or Needs Review.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Data Imputation</span> Physics-informed interpolation & peer regression for continuous downstream feeds.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Raw Data Integrity</span> Strictly preserves original observations while attaching transparent quality flags.</div>
    </div>
    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-highlight">Weather Data Ingestion</span> Ingests multi-sensor telemetry (IMD AWS standard feeds) with timestamp alignment.</div>
    </div>
  </div>

  <!-- RIGHT COLUMN -->
  <div class="right-column">
    <svg class="connector-canvas" viewBox="0 0 1092 955">
      <!-- Yellow connector lines mimicking reference slide -->
      <g stroke="#facc15" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round">
        <!-- Ingestion (bottom center: 350, 85) to Backend (top center: 350, 200) -->
        <path d="M 350 85 L 350 200" />
        
        <!-- SQLite (right center: 220, 150) to Backend bus -->
        <path d="M 220 150 L 260 150 L 260 200" />
        
        <!-- Backend (bottom center: 350, 280) to Web App (top center: 125, 320) -->
        <path d="M 350 280 L 350 300 L 125 300 L 125 320" />
        
        <!-- Web App (bottom center: 125, 385) to MapLibre (top: 102, 460) and Recharts (top: 287, 460) -->
        <path d="M 125 385 L 125 425 L 102 425 L 102 460" />
        <path d="M 125 425 L 287 425 L 287 460" />

        <!-- Backend main bus (right center: 460, 240) to Right Trunk (X = 510) -->
        <path d="M 460 240 L 510 240" />
        
        <!-- Vertical Trunk at X = 510 from Y = 48 to Y = 648 -->
        <path d="M 510 48 L 510 648" />
        
        <!-- Horizontal branches from Trunk into each microservice box (left: 560) -->
        <path d="M 510 48 L 560 48" />
        <path d="M 510 123 L 560 123" />
        <path d="M 510 198 L 560 198" />
        <path d="M 510 273 L 560 273" />
        <path d="M 510 348 L 560 348" />
        <path d="M 510 423 L 560 423" />
        <path d="M 510 498 L 560 498" />
        <path d="M 510 573 L 560 573" />
        <path d="M 510 648 L 560 648" />

        <!-- Postgres node (right center: 930, 573) to Postgres Elephant Logo (left center: 955, 573) -->
        <path d="M 930 573 L 955 573" />
      </g>
    </svg>

    <!-- Node 1: AWS Telemetry Ingestion -->
    <div class="diagram-node" id="node-ingest">
      <div class="node-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
      </div>
      <div>
        <div class="node-title">AWS Telemetry Ingest</div>
        <div class="node-sub">Temp • Pressure • Humidity</div>
      </div>
    </div>

    <!-- Node 2: SQLite Local Replay -->
    <div class="diagram-node" id="node-sqlite">
      <div class="node-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
      </div>
      <div>
        <div class="node-title">SQLite Cache</div>
        <div class="node-sub">Edge Replay & Offline</div>
      </div>
    </div>

    <!-- Central Node: FastAPI Backend -->
    <div class="diagram-node" id="node-backend">
      <div class="node-icon">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
      </div>
      <div>
        <div class="node-title" style="font-size:16px; color:#b91c1c;">FastAPI Backend</div>
        <div class="node-sub">Python 3.12 Asynchronous Core</div>
      </div>
    </div>

    <!-- Node 4: Web Applications -->
    <div class="diagram-node" id="node-web">
      <div class="node-icon">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
      </div>
      <div>
        <div class="node-title">Web Application</div>
        <div class="node-sub">Next.js 14 & React 18</div>
      </div>
    </div>

    <!-- Node 5: MapLibre GL -->
    <div class="diagram-node" id="node-map">
      <div class="node-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>
      </div>
      <div>
        <div class="node-title">MapLibre GL</div>
        <div class="node-sub">Station Geo Map</div>
      </div>
    </div>

    <!-- Node 6: Recharts Graphs -->
    <div class="diagram-node" id="node-charts">
      <div class="node-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
      </div>
      <div>
        <div class="node-title">Recharts Visuals</div>
        <div class="node-sub">Diurnal Multi-Trace</div>
      </div>
    </div>

    <!-- RIGHT MICROSERVICES / MODULES -->
    <div class="diagram-node right-stack-node" id="node-range-qc">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
      </div>
      <div>
        <div class="node-title">Physical Limits & Step QC</div>
        <div class="node-sub">WMO Range Bounds & Sudden Step Jump Detection</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-cusum">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2"><path d="M3 3v18h18"/><path d="M18 9l-5 5-4-4-6 6"/></svg>
      </div>
      <div>
        <div class="node-title">CUSUM Drift Detector</div>
        <div class="node-sub">Cumulative Sum Tracking for Slow Sensor Offset Decay</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-lightgbm">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><circle cx="15.5" cy="15.5" r="1.5"/><path d="M8.5 15.5l7-7"/></svg>
      </div>
      <div>
        <div class="node-title">LightGBM & Scikit-learn</div>
        <div class="node-sub">Multivariate GBDT & Isolation Forest Scoring</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-spatial">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
      </div>
      <div>
        <div class="node-title">Spatial Consensus Engine</div>
        <div class="node-sub">Peer Station Comparison with Elevation & Distance Weighting</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-triage">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
      </div>
      <div>
        <div class="node-title">Decision & Triage Matrix</div>
        <div class="node-sub">Likely Weather vs Suspected Hardware Fault vs Needs Review</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-impute">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" stroke-width="2"><path d="M12 20v-6M6 20V10M18 20V4"/></svg>
      </div>
      <div>
        <div class="node-title">Data Imputation Engine</div>
        <div class="node-sub">Physics-Informed Linear / Neighbor Imputation</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-alerts">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
      </div>
      <div>
        <div class="node-title">Operator Alert Service</div>
        <div class="node-sub">Actionable Diagnoses, Severity Tags & Root-Cause Explanations</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-postgres">
      <div class="node-icon">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>
      </div>
      <div>
        <div class="node-title">PostgreSQL Central Store</div>
        <div class="node-sub">High-Volume Historical Telemetry Archive via psycopg</div>
      </div>
    </div>

    <div class="diagram-node right-stack-node" id="node-archive">
      <div class="node-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
      </div>
      <div>
        <div class="node-title">Raw Telemetry Archive</div>
        <div class="node-sub">Immutable Observations Preserved with Transparent Flags</div>
      </div>
    </div>

    <!-- Big Postgres Elephant Badge on Right Margin (like reference slide) -->
    <svg class="postgres-badge" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="45" fill="#336791"/>
      <path d="M50 20 C36 20 28 28 28 40 C28 50 32 58 36 68 L36 82 L46 82 L46 72 C48 72 52 72 54 72 L54 82 L64 82 L64 68 C68 58 72 50 72 40 C72 28 64 20 50 20 Z" fill="#ffffff" opacity="0.95"/>
      <circle cx="40" cy="38" r="3.5" fill="#336791"/>
      <circle cx="60" cy="38" r="3.5" fill="#336791"/>
      <path d="M38 52 Q50 62 62 52" stroke="#336791" stroke-width="3" fill="none"/>
      <path d="M47 50 L47 70 C47 74 53 74 53 70 L53 50" stroke="#336791" stroke-width="2.5" fill="none"/>
    </svg>

  </div>
</div>

</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML saved: {OUTPUT_HTML}")


def render_png():
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    edge_exe = next((p for p in edge_paths if os.path.exists(p)), None)
    if not edge_exe:
        print("Edge not found!")
        return

    file_url = "file:///" + os.path.abspath(OUTPUT_HTML).replace("\\", "/")
    cmd = [
        edge_exe,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1920,1080",
        f"--screenshot={OUTPUT_PNG}",
        file_url
    ]
    subprocess.run(cmd, check=True)
    print(f"PNG rendered: {OUTPUT_PNG}")


def create_pptx():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Slide border (black outline)
    border_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0.08), Inches(0.08), Inches(13.173), Inches(7.34)
    )
    border_shape.fill.background()
    border_shape.line.color.rgb = RGBColor(30, 41, 59)
    border_shape.line.width = Pt(3)

    # 1. Header: Team Badge
    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.35), Inches(0.25), Inches(2.2), Inches(0.65)
    )
    badge.fill.background()
    badge.line.color.rgb = RGBColor(37, 99, 235)
    badge.line.width = Pt(2.5)
    p = badge.text_frame.paragraphs[0]
    p.text = "Team SkyGuard"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = RGBColor(29, 78, 216)
    p.alignment = PP_ALIGN.CENTER

    # 2. Header: Title
    title_box = slide.shapes.add_textbox(Inches(3.2), Inches(0.2), Inches(6.8), Inches(0.75))
    tf = title_box.text_frame
    p = tf.paragraphs[0]
    p.text = "TECHNICAL APPROACH"
    p.font.size = Pt(30)
    p.font.bold = True
    p.font.color.rgb = RGBColor(26, 42, 90)
    p.alignment = PP_ALIGN.CENTER

    # 3. Header: SIH Badge
    sih_box = slide.shapes.add_textbox(Inches(10.2), Inches(0.18), Inches(2.8), Inches(0.85))
    tf = sih_box.text_frame
    p = tf.paragraphs[0]
    p.text = "SMART INDIA HACKATHON 2024"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 23, 42)
    p.alignment = PP_ALIGN.RIGHT

    # 4. Left Dashed Container
    left_box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.35), Inches(1.05), Inches(5.3), Inches(6.2)
    )
    left_box.fill.background()
    left_box.line.color.rgb = RGBColor(37, 99, 235)
    left_box.line.width = Pt(2)

    tf_left = left_box.text_frame
    tf_left.word_wrap = True
    tf_left.margin_left = Inches(0.18)
    tf_left.margin_right = Inches(0.18)
    tf_left.margin_top = Inches(0.15)
    tf_left.margin_bottom = Inches(0.15)

    bullets = [
        ("Frontend", "Next.js 14 for reactive operator web app and React 18 for component lifecycle."),
        ("MapLibre GL", "for interactive geospatial mapping of weather stations with health badges."),
        ("Recharts", "for real-time diurnal trend curves (temperature, pressure, humidity)."),
        ("FastAPI & Python 3.12", "as a high-performance, asynchronous REST backend framework."),
        ("PostgreSQL", "for central observation management, and SQLite for edge/offline replay."),
        ("LightGBM & Scikit-learn", "ML models for multivariate anomaly scoring."),
        ("CUSUM Algorithm", "for continuous tracking of slow sensor calibration drift."),
        ("Range & Step QC", "WMO-standard physical limit checks and rate-of-change jump detection."),
        ("Spatial Consensus Engine", "Cross-station validation with elevation & distance weighting."),
        ("Decision Triage", "Classifies events into Real Weather, Suspected Fault, or Needs Review."),
        ("Data Imputation", "Physics-informed interpolation for continuous downstream data feeds."),
        ("Raw Data Integrity", "Preserves original observations with non-destructive quality flags."),
        ("Weather Data Ingestion", "Ingests multi-sensor telemetry (IMD AWS standard feeds) reliably.")
    ]

    for i, (hl, desc) in enumerate(bullets):
        p = tf_left.paragraphs[0] if i == 0 else tf_left.add_paragraph()
        p.space_before = Pt(2.5)
        p.space_after = Pt(2.5)
        
        # Diamond symbol
        r_sym = p.add_run()
        r_sym.text = "❖ "
        r_sym.font.bold = True
        r_sym.font.size = Pt(9.5)
        r_sym.font.color.rgb = RGBColor(220, 38, 38)

        # Highlighted term
        r_hl = p.add_run()
        r_hl.text = hl + " "
        r_hl.font.bold = True
        r_hl.font.size = Pt(9.5)
        r_hl.font.color.rgb = RGBColor(220, 38, 38)

        # Description
        r_desc = p.add_run()
        r_desc.text = desc
        r_desc.font.bold = False
        r_desc.font.size = Pt(9.5)
        r_desc.font.color.rgb = RGBColor(30, 41, 59)

    # 5. Right Architecture Diagram Blocks
    nodes = [
        # (title, sub, left, top, width, height, border_rgb, fill_rgb)
        ("AWS Telemetry Ingest", "Temp • Pressure • Humidity", 7.4, 1.15, 2.3, 0.52, RGBColor(59, 130, 246), RGBColor(239, 246, 255)),
        ("SQLite Local Cache", "Edge Replay & Offline", 5.9, 1.95, 1.8, 0.52, RGBColor(100, 116, 139), RGBColor(248, 250, 252)),
        ("FastAPI Backend", "Python 3.12 Core", 7.4, 2.7, 2.2, 0.65, RGBColor(239, 68, 68), RGBColor(254, 242, 242)),
        ("Web Application", "Next.js 14 / React 18", 5.9, 3.8, 1.8, 0.52, RGBColor(2, 132, 199), RGBColor(240, 249, 255)),
        ("MapLibre GL", "Station Geo Map", 5.9, 4.9, 1.6, 0.52, RGBColor(5, 150, 105), RGBColor(240, 253, 244)),
        ("Recharts Visuals", "Diurnal Multi-Trace", 7.7, 4.9, 1.6, 0.52, RGBColor(217, 119, 6), RGBColor(255, 251, 235)),
        
        # Right Microservices Stack
        ("Physical Limits & Step QC", "WMO Bounds & Step Tests", 9.7, 1.15, 3.1, 0.48, RGBColor(99, 102, 241), RGBColor(255, 255, 255)),
        ("CUSUM Drift Detector", "Calibration Drift Tracking", 9.7, 1.75, 3.1, 0.48, RGBColor(234, 179, 8), RGBColor(255, 255, 255)),
        ("LightGBM ML Scorer", "Multivariate Anomaly GBDT", 9.7, 2.35, 3.1, 0.48, RGBColor(139, 92, 246), RGBColor(255, 255, 255)),
        ("Spatial Consensus Engine", "Peer Correlation Check", 9.7, 2.95, 3.1, 0.48, RGBColor(14, 165, 233), RGBColor(255, 255, 255)),
        ("Decision & Triage Logic", "Weather vs Fault vs Review", 9.7, 3.55, 3.1, 0.48, RGBColor(16, 185, 129), RGBColor(236, 253, 245)),
        ("Data Imputation Engine", "Physics-Informed Feed", 9.7, 4.15, 3.1, 0.48, RGBColor(6, 182, 212), RGBColor(255, 255, 255)),
        ("Operator Alert Service", "Root-Cause Explanations", 9.7, 4.75, 3.1, 0.48, RGBColor(249, 115, 22), RGBColor(255, 247, 237)),
        ("PostgreSQL Central Store", "Historical Telemetry Archive", 9.7, 5.35, 3.1, 0.48, RGBColor(37, 99, 235), RGBColor(239, 246, 255)),
        ("Raw Telemetry Archive", "Immutable Observation Store", 9.7, 5.95, 3.1, 0.48, RGBColor(100, 116, 139), RGBColor(248, 250, 252)),
    ]

    for title, sub, l, t, w, h, b_col, f_col in nodes:
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = f_col
        shape.line.color.rgb = b_col
        shape.line.width = Pt(1.5)
        
        tf_n = shape.text_frame
        tf_n.word_wrap = True
        tf_n.margin_left = Inches(0.08)
        tf_n.margin_right = Inches(0.08)
        tf_n.margin_top = Inches(0.04)
        tf_n.margin_bottom = Inches(0.04)
        
        p1 = tf_n.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(10.5)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(30, 41, 59)
        p1.alignment = PP_ALIGN.CENTER
        
        p2 = tf_n.add_paragraph()
        p2.text = sub
        p2.font.size = Pt(8.0)
        p2.font.bold = False
        p2.font.color.rgb = RGBColor(100, 116, 139)
        p2.alignment = PP_ALIGN.CENTER

    prs.save(OUTPUT_PPTX)
    print(f"PPTX saved: {OUTPUT_PPTX}")

if __name__ == "__main__":
    create_html()
    render_png()
    create_pptx()
