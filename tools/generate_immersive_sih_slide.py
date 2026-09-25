"""
Generate the complete, accurate Technical Approach slide with:
- Team Name: 'Dark Mode' (or 'Team Dark Mode')
- Explicit PyTorch CausalTCN & CausalGRU Deep Neural Networks
- LightGBM & Scikit-learn Tree Ensembles
- Full meteorological quality control, spatial consensus, and triage flow
- Bottom value bar (Real-Time Monitoring, AI-Powered Reliability, Transparent & Trusted)
- Formats: High-Res PNG (1920x1080), HTML, and PPTX (16:9)
"""

import os
import subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_HTML = r"c:\Users\deepa\OneDrive\Desktop\Sih 73\sih73_technical_approach_neural_darkmode.html"
OUTPUT_PNG = r"c:\Users\deepa\OneDrive\Desktop\Sih 73\sih73_technical_approach_neural_darkmode.png"
OUTPUT_PPTX = r"c:\Users\deepa\OneDrive\Desktop\Sih 73\sih73_technical_approach_neural_darkmode.pptx"

def create_html():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Technical Approach - Team Dark Mode - SIH 2024</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1920px;
    height: 1080px;
    background: #ffffff;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
    color: #0f172a;
    position: relative;
    overflow: hidden;
    padding: 14px 22px;
  }

  /* Slide Outer Border */
  .slide-border {
    position: absolute;
    top: 6px; left: 6px; right: 6px; bottom: 6px;
    border: 3px solid #1e293b;
    pointer-events: none;
    z-index: 100;
  }

  /* Header Bar */
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 72px;
    padding: 0 10px;
    border-bottom: 2px solid #cbd5e1;
    margin-bottom: 12px;
  }

  /* Team Name Badge */
  .team-badge-dark {
    background: #0f172a;
    border: 2.5px solid #38bdf8;
    border-radius: 9999px;
    padding: 6px 26px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.2);
  }

  .team-dot {
    width: 12px;
    height: 12px;
    background: #38bdf8;
    border-radius: 50%;
    box-shadow: 0 0 8px #38bdf8;
  }

  .team-badge-text {
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .title-block {
    text-align: center;
  }

  .slide-title {
    font-size: 42px;
    font-weight: 900;
    font-family: 'Times New Roman', Georgia, serif;
    color: #1a2a5a;
    letter-spacing: 3px;
    line-height: 1.05;
  }

  .slide-subtitle {
    font-size: 13.5px;
    font-weight: 600;
    color: #64748b;
    letter-spacing: 0.5px;
  }

  .sih-logo-block {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .sih-text {
    text-align: right;
    font-weight: 900;
    font-size: 14.5px;
    line-height: 1.15;
    color: #0f172a;
  }

  .sih-year {
    font-size: 18px;
    color: #0f172a;
    font-weight: 900;
  }

  /* Main Split Layout */
  .main-container {
    display: flex;
    height: 870px;
    gap: 18px;
  }

  /* Left Column: 40% width */
  .left-column {
    flex: 0 0 740px;
    border: 2px dashed #2563eb;
    border-radius: 10px;
    padding: 14px 18px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .left-column-title {
    font-size: 16px;
    font-weight: 800;
    color: #1e3a8a;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1.5px solid #cbd5e1;
    padding-bottom: 6px;
    margin-bottom: 6px;
  }

  .tech-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 13.2px;
    line-height: 1.32;
    color: #1e293b;
    background: #ffffff;
    padding: 5px 8px;
    border-radius: 5px;
    border: 1px solid #e2e8f0;
  }

  .bullet-icon {
    color: #dc2626;
    font-size: 14px;
    font-weight: bold;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .tech-name {
    font-weight: 800;
    color: #dc2626;
  }

  .tech-role {
    font-weight: 700;
    color: #2563eb;
    margin-right: 4px;
  }

  .simple-desc {
    color: #334155;
    font-weight: 500;
  }

  /* Right Column: Architectural Diagram */
  .right-column {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .diagram-wrapper {
    flex: 1;
    position: relative;
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.02);
  }

  .diagram-header-strip {
    position: absolute;
    top: 10px; left: 16px; right: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1.5px solid #f1f5f9;
    padding-bottom: 6px;
    z-index: 10;
  }

  .diagram-title {
    font-size: 16px;
    font-weight: 800;
    color: #1e3a8a;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }

  .diagram-tagline {
    font-size: 12px;
    font-weight: 700;
    color: #2563eb;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }

  /* Connector SVG Canvas */
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
    border-radius: 7px;
    padding: 5px 10px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
  }

  .node-title {
    font-size: 13px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.15;
  }

  .node-sub {
    font-size: 10.5px;
    color: #64748b;
    font-weight: 600;
  }

  .node-icon {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border-radius: 5px;
    background: #f8fafc;
  }

  /* Central FastAPI Backend */
  #node-backend {
    top: 185px; left: 240px; width: 220px; height: 75px;
    border: 2.5px solid #ef4444; background: #fff5f5;
    padding: 8px 12px;
    border-radius: 9px;
  }

  /* Ingest & Cache */
  #node-ingest {
    top: 50px; left: 240px; width: 220px; height: 58px;
    border-color: #3b82f6; background: #eff6ff;
  }

  #node-sqlite {
    top: 125px; left: 20px; width: 195px; height: 58px;
    border-color: #64748b; background: #f8fafc;
  }

  /* Frontend Clients */
  #node-web {
    top: 310px; left: 20px; width: 195px; height: 62px;
    border-color: #0284c7; background: #f0f9ff;
  }

  #node-map {
    top: 440px; left: 15px; width: 175px; height: 58px;
    border-color: #059669; background: #f0fdf4;
  }

  #node-charts {
    top: 440px; left: 205px; width: 175px; height: 58px;
    border-color: #f59e0b; background: #fffbeb;
  }

  /* Right Microservices Stack (Left = 570px, Width = 385px, Height = 52px) */
  .right-stack-node {
    left: 570px; width: 385px; height: 52px;
  }
  #node-range-qc { top: 45px; border-color: #ef4444; background: #fef2f2; }
  #node-cusum    { top: 105px; border-color: #eab308; background: #fefce8; }
  #node-tcn      { top: 165px; border-color: #8b5cf6; background: #f5f3ff; border-width: 2.5px; }
  #node-lightgbm { top: 225px; border-color: #6366f1; background: #eef2ff; }
  #node-spatial  { top: 285px; border-color: #0ea5e9; background: #f0f9ff; }
  #node-triage   { top: 345px; border-color: #10b981; background: #ecfdf5; }
  #node-impute   { top: 405px; border-color: #06b6d4; background: #ecfeff; }
  #node-alerts   { top: 465px; border-color: #f97316; background: #fff7ed; }
  #node-postgres { top: 525px; border-color: #2563eb; background: #eff6ff; }
  #node-archive  { top: 585px; border-color: #64748b; background: #f8fafc; }

  /* Operators Target Node */
  #node-operators {
    top: 525px; left: 980px; width: 120px; height: 75px;
    border: 2px solid #0f172a; background: #0f172a; color: #ffffff;
    border-radius: 8px; flex-direction: column; justify-content: center; text-align: center; gap: 4px;
    padding: 6px;
  }

  /* Bottom Value Strip */
  .bottom-strip {
    height: 70px;
    background: #f1f5f9;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: space-around;
    padding: 0 20px;
  }

  .strip-item {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .strip-icon {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .strip-title {
    font-size: 14px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: 0.5px;
  }

  .strip-desc {
    font-size: 12px;
    color: #64748b;
    font-weight: 600;
  }
</style>
</head>
<body>

<div class="slide-border"></div>

<div class="header">
  <!-- Team Name Dark Mode Pill -->
  <div class="team-badge-dark">
    <div class="team-dot"></div>
    <div class="team-badge-text">Dark Mode</div>
  </div>

  <!-- Title & Subtitle -->
  <div class="title-block">
    <div class="slide-title">TECHNICAL APPROACH</div>
    <div class="slide-subtitle">SIH Problem Statement 26073 • Automated Weather Station Sensor Anomaly Detection</div>
  </div>

  <!-- SIH Official Logo Block -->
  <div class="sih-logo-block">
    <svg width="46" height="46" viewBox="0 0 100 100">
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
  <!-- LEFT COLUMN: Technology & Plain-English Explanations -->
  <div class="left-column">
    <div class="left-column-title">
      <span>Key Components & Approach</span>
      <span style="font-size:11px; color:#2563eb; font-weight:700;">Verified Stack</span>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">Frontend</span> <span class="tech-role">(Operator UI):</span> <span class="simple-desc">Next.js 14 & React 18 web dashboard for interactive monitoring, alerts, and live station health metrics.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">MapLibre GL</span> <span class="tech-role">(Station Map):</span> <span class="simple-desc">Interactive geospatial map of AWS weather stations with color-coded health badges (Green, Red, Amber).</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">Recharts</span> <span class="tech-role">(Diurnal Graphs):</span> <span class="simple-desc">Smooth 24-hour diurnal curves for temperature, pressure, and humidity to easily visualize anomalies.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">FastAPI & Python 3.12</span> <span class="tech-role">(Core Backend):</span> <span class="simple-desc">Asynchronous REST backend for telemetry ingestion, neural model scoring, and real-time alert delivery.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">PostgreSQL Store</span> <span class="tech-role">(Central Database):</span> <span class="simple-desc">High-volume historical repository via psycopg for raw observations, QC flags, and incident records.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">SQLite Cache</span> <span class="tech-role">(Offline / Local):</span> <span class="simple-desc">Local edge cache and offline replay engine ensuring continuous operations when internet is offline.</span></div>
    </div>

    <div class="tech-item" style="border-left: 3px solid #8b5cf6;">
      <span class="bullet-icon" style="color:#8b5cf6;">❖</span>
      <div><span class="tech-name" style="color:#8b5cf6;">PyTorch CausalTCN</span> <span class="tech-role">(Deep Neural Network):</span> <span class="simple-desc">Dilated causal 1D convolutions & CausalGRU scanning time-series history to catch sequential breakdown without data leakage.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">LightGBM & Scikit-learn</span> <span class="tech-role">(Tree Ensemble):</span> <span class="simple-desc">Gradient-boosted decision trees and Isolation Forest for tabular feature interactions and anomaly scoring.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">CUSUM Algorithm</span> <span class="tech-role">(Drift Detector):</span> <span class="simple-desc">Cumulative sum tracking detecting gradual sensor calibration loss and persistent bias decay over days.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">Physical Limits & Step QC</span> <span class="tech-role">(Rule Checks):</span> <span class="simple-desc">WMO physical range limits and sudden rate-of-change jump detection for invalid telemetry readings.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">Spatial Consensus</span> <span class="tech-role">(Peer Validation):</span> <span class="simple-desc">Cross-validates with suitable nearby stations accounting for distance and elevation differences.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">Decision Triage</span> <span class="tech-role">(Classifier):</span> <span class="simple-desc">Separates real weather events from sensor hardware faults, routing ambiguous cases to manual review.</span></div>
    </div>

    <div class="tech-item">
      <span class="bullet-icon">❖</span>
      <div><span class="tech-name">Physics-Based Imputation</span> <span class="tech-role">(Gap Filling):</span> <span class="simple-desc">Clearly labeled estimated readings for continuity, preserving original raw observations untouched.</span></div>
    </div>
  </div>

  <!-- RIGHT COLUMN: Screen-Fitted Architecture Schematic -->
  <div class="right-column">
    <div class="diagram-wrapper">
      <div class="diagram-header-strip">
        <div class="diagram-title">System Architecture</div>
        <div class="diagram-tagline">From Data to Insights, For a Safer Tomorrow</div>
      </div>

      <svg class="connector-canvas" viewBox="0 0 1110 655">
        <g stroke="#facc15" stroke-width="2.8" fill="none" stroke-linecap="round" stroke-linejoin="round">
          <!-- Ingest to Backend -->
          <path d="M 350 108 L 350 185" />
          
          <!-- SQLite to Backend -->
          <path d="M 215 154 L 240 154 L 240 205" />
          
          <!-- Backend to Frontend -->
          <path d="M 350 260 L 350 285 L 117 285 L 117 310" />
          
          <!-- Frontend to MapLibre and Recharts -->
          <path d="M 117 372 L 117 410 L 102 410 L 102 440" />
          <path d="M 117 410 L 292 410 L 292 440" />

          <!-- Backend main bus (460, 222) to Right Trunk (X = 515) -->
          <path d="M 460 222 L 515 222" />
          
          <!-- Vertical Trunk at X = 515 from Y = 71 to Y = 611 -->
          <path d="M 515 71 L 515 611" />
          
          <!-- Horizontal branches from Trunk into each microservice box (left: 570) -->
          <path d="M 515 71 L 570 71" />
          <path d="M 515 131 L 570 131" />
          <path d="M 515 191 L 570 191" />
          <path d="M 515 251 L 570 251" />
          <path d="M 515 311 L 570 311" />
          <path d="M 515 371 L 570 371" />
          <path d="M 515 431 L 570 431" />
          <path d="M 515 491 L 570 491" />
          <path d="M 515 551 L 570 551" />
          <path d="M 515 611 L 570 611" />

          <!-- Postgres node to Operators badge on far right -->
          <path d="M 955 551 L 980 551" />
        </g>
      </svg>

      <!-- Node 1: AWS Telemetry Ingestion -->
      <div class="diagram-node" id="node-ingest">
        <div class="node-icon" style="background:#dbeafe;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
        </div>
        <div>
          <div class="node-title">AWS Telemetry Ingest</div>
          <div class="node-sub">Temp • Pressure • Humidity</div>
        </div>
      </div>

      <!-- Node 2: SQLite Local Replay -->
      <div class="diagram-node" id="node-sqlite">
        <div class="node-icon" style="background:#f1f5f9;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2.2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
        </div>
        <div>
          <div class="node-title">SQLite Cache</div>
          <div class="node-sub">Edge Replay & Offline Support</div>
        </div>
      </div>

      <!-- Central Node: FastAPI Backend -->
      <div class="diagram-node" id="node-backend">
        <div class="node-icon" style="background:#fee2e2; width:38px; height:38px;">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
        </div>
        <div>
          <div class="node-title" style="font-size:15px; color:#b91c1c;">FastAPI Backend</div>
          <div class="node-sub" style="color:#7f1d1d;">Python 3.12 Asynchronous Core</div>
        </div>
      </div>

      <!-- Node 4: Web Applications -->
      <div class="diagram-node" id="node-web">
        <div class="node-icon" style="background:#e0f2fe;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        </div>
        <div>
          <div class="node-title">Web Application</div>
          <div class="node-sub">Next.js 14 & React 18</div>
        </div>
      </div>

      <!-- Node 5: MapLibre GL -->
      <div class="diagram-node" id="node-map">
        <div class="node-icon" style="background:#dcfce7;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></svg>
        </div>
        <div>
          <div class="node-title">MapLibre GL</div>
          <div class="node-sub">Station Geo Map</div>
        </div>
      </div>

      <!-- Node 6: Recharts Graphs -->
      <div class="diagram-node" id="node-charts">
        <div class="node-icon" style="background:#fef3c7;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        </div>
        <div>
          <div class="node-title">Recharts Visuals</div>
          <div class="node-sub">Diurnal Multi-Trace</div>
        </div>
      </div>

      <!-- RIGHT MICROSERVICES / MODULES -->
      <div class="diagram-node right-stack-node" id="node-range-qc">
        <div class="node-icon" style="background:#fee2e2;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <div>
          <div class="node-title">Physical Limits & Step QC</div>
          <div class="node-sub">WMO Range Bounds & Sudden Step-Jump Detection</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-cusum">
        <div class="node-icon" style="background:#fef9c3;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ca8a04" stroke-width="2.2"><path d="M3 3v18h18"/><path d="M18 9l-5 5-4-4-6 6"/></svg>
        </div>
        <div>
          <div class="node-title">CUSUM Drift Detector</div>
          <div class="node-sub">Cumulative Sum Tracking for Slow Sensor Offset Decay</div>
        </div>
      </div>

      <!-- Explicit PyTorch Neural Network Node -->
      <div class="diagram-node right-stack-node" id="node-tcn">
        <div class="node-icon" style="background:#f3e8ff;">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2.2"><path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/><path d="M12 6v6l4 2"/></svg>
        </div>
        <div>
          <div class="node-title" style="color:#6b21a8;">PyTorch CausalTCN Neural Network</div>
          <div class="node-sub" style="color:#7e22ce;">Dilated Causal 1D Convolutions + CausalGRU</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-lightgbm">
        <div class="node-icon" style="background:#e0e7ff;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2.2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><circle cx="15.5" cy="15.5" r="1.5"/><path d="M8.5 15.5l7-7"/></svg>
        </div>
        <div>
          <div class="node-title">LightGBM & Scikit-learn</div>
          <div class="node-sub">Multivariate GBDT & Isolation Forest Scoring</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-spatial">
        <div class="node-icon" style="background:#e0f2fe;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
        </div>
        <div>
          <div class="node-title">Spatial Consensus Engine</div>
          <div class="node-sub">Peer Station Comparison with Elevation & Distance Weighting</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-triage">
        <div class="node-icon" style="background:#d1fae5;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        </div>
        <div>
          <div class="node-title">Decision & Triage Matrix</div>
          <div class="node-sub">Likely Weather vs Suspected Hardware Fault vs Needs Review</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-impute">
        <div class="node-icon" style="background:#cffafe;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0891b2" stroke-width="2.2"><path d="M12 20v-6M6 20V10M18 20V4"/></svg>
        </div>
        <div>
          <div class="node-title">Data Imputation Engine</div>
          <div class="node-sub">Physics-Informed Linear / Neighbor Imputation</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-alerts">
        <div class="node-icon" style="background:#ffedd5;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ea580c" stroke-width="2.2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        </div>
        <div>
          <div class="node-title">Operator Alert Service</div>
          <div class="node-sub">Actionable Diagnoses, Severity Tags & Root-Cause Explanations</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-postgres">
        <div class="node-icon" style="background:#dbeafe;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.2"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>
        </div>
        <div>
          <div class="node-title">PostgreSQL Central Store</div>
          <div class="node-sub">High-Volume Telemetry Archive & Incident Records</div>
        </div>
      </div>

      <div class="diagram-node right-stack-node" id="node-archive">
        <div class="node-icon" style="background:#f1f5f9;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2.2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
        </div>
        <div>
          <div class="node-title">Raw Telemetry Archive</div>
          <div class="node-sub">Immutable Observations Preserved with Transparent Flags</div>
        </div>
      </div>

      <!-- Right Target: Operators -->
      <div class="diagram-node" id="node-operators">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2.2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        <div style="font-size:12px; font-weight:800; color:#ffffff;">Operators</div>
        <div style="font-size:9.5px; color:#94a3b8; font-weight:600;">Informed Actions</div>
      </div>

    </div>

    <!-- Bottom Value Strip -->
    <div class="bottom-strip">
      <div class="strip-item">
        <div class="strip-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2.2"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/></svg>
        </div>
        <div>
          <div class="strip-title">REAL-TIME MONITORING</div>
          <div class="strip-desc">From raw AWS sensors to operational insights</div>
        </div>
      </div>

      <div class="strip-item">
        <div class="strip-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2.2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        </div>
        <div>
          <div class="strip-title">AI-POWERED RELIABILITY</div>
          <div class="strip-desc">PyTorch CausalTCN + GBDT Ensemble Verification</div>
        </div>
      </div>

      <div class="strip-item">
        <div class="strip-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
        </div>
        <div>
          <div class="strip-title">TRANSPARENT & TRUSTED</div>
          <div class="strip-desc">Original records preserved with diagnostic explanations</div>
        </div>
      </div>
    </div>

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
        MSO_SHAPE.RECTANGLE, Inches(0.06), Inches(0.06), Inches(13.213), Inches(7.38)
    )
    border_shape.fill.background()
    border_shape.line.color.rgb = RGBColor(30, 41, 59)
    border_shape.line.width = Pt(2.5)

    # 1. Header: Dark Mode Team Badge
    badge = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.35), Inches(0.18), Inches(2.2), Inches(0.62)
    )
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(15, 23, 42)
    badge.line.color.rgb = RGBColor(56, 189, 248)
    badge.line.width = Pt(2)
    p = badge.text_frame.paragraphs[0]
    p.text = "Dark Mode"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.alignment = PP_ALIGN.CENTER

    # 2. Header: Title & Subtitle
    title_box = slide.shapes.add_textbox(Inches(2.8), Inches(0.1), Inches(7.6), Inches(0.8))
    tf = title_box.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "TECHNICAL APPROACH"
    p1.font.size = Pt(27)
    p1.font.bold = True
    p1.font.color.rgb = RGBColor(26, 42, 90)
    p1.alignment = PP_ALIGN.CENTER
    
    p2 = tf.add_paragraph()
    p2.text = "SIH Problem Statement 26073 • Automated Weather Station Sensor Anomaly Detection"
    p2.font.size = Pt(9.5)
    p2.font.bold = True
    p2.font.color.rgb = RGBColor(100, 116, 139)
    p2.alignment = PP_ALIGN.CENTER

    # 3. Header: SIH Badge
    sih_box = slide.shapes.add_textbox(Inches(10.5), Inches(0.16), Inches(2.5), Inches(0.8))
    tf = sih_box.text_frame
    p = tf.paragraphs[0]
    p.text = "SMART INDIA HACKATHON 2024"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = RGBColor(15, 23, 42)
    p.alignment = PP_ALIGN.RIGHT

    # 4. Left Dashed Container (40% width)
    left_box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.35), Inches(1.0), Inches(5.2), Inches(6.25)
    )
    left_box.fill.solid()
    left_box.fill.fore_color.rgb = RGBColor(248, 250, 252)
    left_box.line.color.rgb = RGBColor(37, 99, 235)
    left_box.line.width = Pt(1.8)

    tf_left = left_box.text_frame
    tf_left.word_wrap = True
    tf_left.margin_left = Inches(0.14)
    tf_left.margin_right = Inches(0.14)
    tf_left.margin_top = Inches(0.1)
    tf_left.margin_bottom = Inches(0.1)

    bullets = [
        ("Frontend", "(Operator UI):", "Next.js 14 & React 18 web dashboard for interactive monitoring and live health metrics."),
        ("MapLibre GL", "(Station Map):", "Interactive geospatial map of AWS stations with color-coded health badges (Green, Red, Amber)."),
        ("Recharts", "(Diurnal Graphs):", "Smooth 24-hour diurnal curves for temperature, pressure, and humidity to easily spot anomalies."),
        ("FastAPI & Python 3.12", "(Core Backend):", "Asynchronous REST backend for telemetry ingestion, neural model scoring, and alert delivery."),
        ("PostgreSQL Store", "(Central DB):", "High-volume historical repository via psycopg for raw observations, flags, and incident logs."),
        ("SQLite Cache", "(Offline / Local):", "Local edge cache and offline replay engine ensuring operations continue when internet is offline."),
        ("PyTorch CausalTCN", "(Deep Neural Net):", "Dilated causal 1D convolutions & CausalGRU scanning time-series history without data leakage."),
        ("LightGBM & Scikit-learn", "(Tree Ensemble):", "Gradient-boosted trees and Isolation Forest for tabular interactions and anomaly scoring."),
        ("CUSUM Algorithm", "(Drift Detector):", "Cumulative sum tracking detecting gradual sensor calibration loss and persistent bias decay."),
        ("Physical Limits & Step QC", "(Rule Checks):", "WMO physical range limits and sudden rate-of-change jump detection for invalid readings."),
        ("Spatial Consensus", "(Peer Validation):", "Cross-validates with nearby stations accounting for distance and elevation differences."),
        ("Decision Triage", "(Classifier):", "Separates real weather events from sensor hardware faults, routing ambiguous cases to review."),
        ("Physics-Based Imputation", "(Gap Filling):", "Clearly labeled estimated readings for continuity, preserving original raw data untouched.")
    ]

    for i, (t_name, t_role, desc) in enumerate(bullets):
        p = tf_left.paragraphs[0] if i == 0 else tf_left.add_paragraph()
        p.space_before = Pt(1.5)
        p.space_after = Pt(1.5)
        
        # Diamond
        r_sym = p.add_run()
        r_sym.text = "❖ "
        r_sym.font.bold = True
        r_sym.font.size = Pt(8.2)
        r_sym.font.color.rgb = RGBColor(220, 38, 38)

        # Tech Name
        r_name = p.add_run()
        r_name.text = t_name + " "
        r_name.font.bold = True
        r_name.font.size = Pt(8.2)
        r_name.font.color.rgb = RGBColor(220, 38, 38)

        # Tech Role
        r_role = p.add_run()
        r_role.text = t_role + " "
        r_role.font.bold = True
        r_role.font.size = Pt(8.2)
        r_role.font.color.rgb = RGBColor(37, 99, 235)

        # Simple Description
        r_desc = p.add_run()
        r_desc.text = desc
        r_desc.font.bold = False
        r_desc.font.size = Pt(8.2)
        r_desc.font.color.rgb = RGBColor(51, 65, 85)

    # 5. Right Architecture Diagram Blocks
    nodes = [
        # (title, sub, left, top, width, height, border_rgb, fill_rgb)
        ("AWS Telemetry Ingest", "Temp • Pressure • Humidity", 7.2, 1.1, 2.2, 0.48, RGBColor(59, 130, 246), RGBColor(239, 246, 255)),
        ("SQLite Cache", "Edge Replay & Offline Support", 5.8, 1.85, 1.8, 0.48, RGBColor(100, 116, 139), RGBColor(248, 250, 252)),
        ("FastAPI Backend", "Python 3.12 Asynchronous Core", 7.2, 2.5, 2.2, 0.6, RGBColor(239, 68, 68), RGBColor(254, 242, 242)),
        ("Web Application", "Next.js 14 & React 18", 5.8, 3.5, 1.8, 0.48, RGBColor(2, 132, 199), RGBColor(240, 249, 255)),
        ("MapLibre GL", "Station Geo Map", 5.7, 4.55, 1.55, 0.48, RGBColor(5, 150, 105), RGBColor(240, 253, 244)),
        ("Recharts Visuals", "Diurnal Multi-Trace", 7.4, 4.55, 1.55, 0.48, RGBColor(217, 119, 6), RGBColor(255, 251, 235)),
        
        # Right Microservices Stack
        ("Physical Limits & Step QC", "WMO Bounds & Step-Jump Detection", 9.5, 1.1, 3.2, 0.44, RGBColor(239, 68, 68), RGBColor(254, 242, 242)),
        ("CUSUM Drift Detector", "Cumulative Sum Sensor Offset Decay", 9.5, 1.62, 3.2, 0.44, RGBColor(234, 179, 8), RGBColor(254, 252, 232)),
        ("PyTorch CausalTCN Neural Net", "Dilated 1D Convolutions & CausalGRU", 9.5, 2.14, 3.2, 0.44, RGBColor(139, 92, 246), RGBColor(245, 243, 255)),
        ("LightGBM & Scikit-learn", "Multivariate GBDT & Isolation Forest", 9.5, 2.66, 3.2, 0.44, RGBColor(99, 102, 241), RGBColor(238, 242, 255)),
        ("Spatial Consensus Engine", "Peer Station Validation with Elevation", 9.5, 3.18, 3.2, 0.44, RGBColor(14, 165, 233), RGBColor(240, 249, 255)),
        ("Decision & Triage Matrix", "Weather vs Fault vs Needs Review", 9.5, 3.70, 3.2, 0.44, RGBColor(16, 185, 129), RGBColor(236, 253, 245)),
        ("Data Imputation Engine", "Physics-Informed Linear / Neighbor Imputation", 9.5, 4.22, 3.2, 0.44, RGBColor(6, 182, 212), RGBColor(236, 254, 255)),
        ("Operator Alert Service", "Actionable Diagnoses & Explanations", 9.5, 4.74, 3.2, 0.44, RGBColor(249, 115, 22), RGBColor(255, 247, 237)),
        ("PostgreSQL Central Store", "Historical Database & Incident Logs", 9.5, 5.26, 3.2, 0.44, RGBColor(37, 99, 235), RGBColor(239, 246, 255)),
        ("Raw Telemetry Archive", "Immutable Observations with Flags", 9.5, 5.78, 3.2, 0.44, RGBColor(100, 116, 139), RGBColor(248, 250, 252)),
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
        tf_n.margin_left = Inches(0.06)
        tf_n.margin_right = Inches(0.06)
        tf_n.margin_top = Inches(0.03)
        tf_n.margin_bottom = Inches(0.03)
        
        p1 = tf_n.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(9.5)
        p1.font.bold = True
        p1.font.color.rgb = RGBColor(15, 23, 42)
        p1.alignment = PP_ALIGN.CENTER
        
        p2 = tf_n.add_paragraph()
        p2.text = sub
        p2.font.size = Pt(7.5)
        p2.font.bold = False
        p2.font.color.rgb = RGBColor(100, 116, 139)
        p2.alignment = PP_ALIGN.CENTER

    # Bottom strip in PPTX
    bot_strip = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(5.8), Inches(6.45), Inches(7.2), Inches(0.8)
    )
    bot_strip.fill.solid()
    bot_strip.fill.fore_color.rgb = RGBColor(241, 245, 249)
    bot_strip.line.color.rgb = RGBColor(203, 213, 225)
    bot_strip.line.width = Pt(1.5)
    tf_b = bot_strip.text_frame
    p_b = tf_b.paragraphs[0]
    p_b.text = "REAL-TIME MONITORING: From sensors to insights  |  AI-POWERED: PyTorch CausalTCN + GBDT  |  TRANSPARENT: Raw data preserved"
    p_b.font.size = Pt(9.5)
    p_b.font.bold = True
    p_b.font.color.rgb = RGBColor(30, 41, 59)
    p_b.alignment = PP_ALIGN.CENTER

    prs.save(OUTPUT_PPTX)
    print(f"PPTX saved: {OUTPUT_PPTX}")

if __name__ == "__main__":
    create_html()
    render_png()
    create_pptx()
