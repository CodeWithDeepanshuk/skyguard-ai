import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "file:///C:/Users/deepa/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const ROOT = "C:/Users/deepa/OneDrive/Desktop/Sih 73";
const OUT = path.join(ROOT, "deliverables");
const RENDER = path.join(OUT, "rendered");
const SCREENSHOT = path.join(OUT, "assets/live-dashboard-viewport.png");

const C = {
  ink: "#101827",
  muted: "#64748B",
  line: "#D9E2EC",
  paper: "#F7FAFC",
  white: "#FFFFFF",
  blue: "#2563EB",
  cyan: "#0EA5E9",
  teal: "#0F766E",
  green: "#16A34A",
  amber: "#D97706",
  red: "#DC2626",
  paleBlue: "#EAF5FB",
  paleGreen: "#EAF8F1",
  paleAmber: "#FFF7E6",
};

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
deck.theme.colorScheme = {
  name: "SkyGuard Grid",
  themeColors: {
    accent1: C.blue, accent2: C.teal, accent3: C.cyan, accent4: C.amber,
    accent5: C.red, accent6: C.green, bg1: C.white, bg2: C.paper,
    tx1: C.ink, tx2: C.muted, dk1: "#000000", dk2: C.ink,
    lt1: C.white, lt2: C.line, hlink: C.blue, folHlink: "#7C3AED",
  },
};

function rect(slide, left, top, width, height, fill = C.white, radius = "rounded-xl", line = C.line) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
    borderRadius: radius,
  });
}

function text(slide, value, left, top, width, height, fontSize = 24, color = C.ink, bold = false, align = "left") {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = value;
  box.text.style = { fontSize, color, bold, typeface: "Helvetica Neue", alignment: align, verticalAlignment: "middle" };
  return box;
}

function pill(slide, value, left, top, width, fill = C.paleBlue, color = C.blue) {
  rect(slide, left, top, width, 34, fill, "rounded-full", "none");
  text(slide, value, left + 12, top + 3, width - 24, 28, 15, color, true, "center");
}

function header(slide, title, eyebrow, number) {
  slide.background.fill = C.white;
  text(slide, eyebrow.toUpperCase(), 42, 24, 900, 28, 14, C.blue, true);
  text(slide, title, 42, 54, 1160, 66, 39, C.ink, true);
  text(slide, String(number).padStart(2, "0"), 1180, 658, 55, 24, 13, C.muted, false, "right");
}

function notes(slide, body, urls = []) {
  const sources = urls.length ? `\n\n[Sources]\n${urls.map((u) => `- ${u}`).join("\n")}\n[/Sources]` : "";
  slide.speakerNotes.textFrame.setText(body + sources);
  slide.speakerNotes.setVisible(true);
}

function metricCard(slide, left, top, width, label, value, detail, fill = C.paper, accent = C.blue) {
  rect(slide, left, top, width, 132, fill, "rounded-xl", "none");
  text(slide, label.toUpperCase(), left + 20, top + 14, width - 40, 24, 13, accent, true);
  text(slide, value, left + 20, top + 41, width - 40, 48, 34, C.ink, true);
  text(slide, detail, left + 20, top + 91, width - 40, 26, 15, C.muted);
}

// 1 — cover, preserving Codex Grid slide-08 split hierarchy and hero media frame.
{
  const s = deck.slides.add();
  s.background.fill = C.white;
  pill(s, "SIH 26073 · PHASE 9", 42, 38, 210);
  text(s, "SkyGuard AI", 42, 132, 560, 78, 54, C.ink, true);
  text(s, "A self-healing weather observation network", 42, 214, 560, 90, 31, C.ink, true);
  text(s, "Detect faults. Preserve genuine weather. Explain every decision. Run live or fully offline.", 42, 326, 560, 100, 22, C.muted);
  pill(s, "578,448 observations", 42, 472, 195, C.paleGreen, C.teal);
  pill(s, "24 Indian stations", 250, 472, 168, C.paleBlue, C.blue);
  pill(s, "51 tests pass", 431, 472, 140, C.paleAmber, C.amber);
  const bytes = await fs.readFile(SCREENSHOT);
  s.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt: "SkyGuard AI live operations dashboard",
    fit: "cover",
    position: { left: 658, top: 42, width: 582, height: 588 },
    geometry: "roundRect",
    borderRadius: "rounded-2xl",
  });
  text(s, "Software · AI/ML · Disaster management", 42, 648, 520, 26, 15, C.muted);
  notes(s, "Open with the decision: SkyGuard is an end-to-end software solution for the AWS anomaly problem, with both controlled offline proof and genuine live observations.");
}

// 2 — problem and target.
{
  const s = deck.slides.add();
  header(s, "The problem is trust—not just thresholding", "SIH problem fit", 2);
  rect(s, 42, 150, 520, 465, C.paleBlue, "rounded-2xl", "none");
  text(s, "Three signals", 72, 178, 450, 36, 18, C.blue, true);
  text(s, "Temperature\nPressure\nRelative humidity", 72, 224, 450, 142, 34, C.ink, true);
  text(s, "A spike may be a failed sensor—or a real regional event. The system must know the difference in real time.", 72, 392, 440, 120, 22, C.muted);
  const reqs = [
    ["Detect", "spikes, drift, frozen and transport faults"],
    ["Distinguish", "genuine weather from sensor failure"],
    ["Explain", "severity, confidence and root cause"],
    ["Act", "correct safely and recommend maintenance"],
  ];
  reqs.forEach(([a, b], i) => {
    const y = 150 + i * 112;
    rect(s, 604, y, 594, 92, i === 1 ? C.paleGreen : C.paper, "rounded-xl", "none");
    text(s, a, 630, y + 17, 145, 28, 20, i === 1 ? C.teal : C.blue, true);
    text(s, b, 790, y + 13, 370, 56, 18, C.ink);
  });
  pill(s, "MANDATORY SOFTWARE SCOPE: COMPLETE", 604, 586, 350, C.paleGreen, C.teal);
  notes(s, "Frame the challenge as trustworthy observations. Emphasize that the public statement asks for real-time anomaly detection, genuine-weather separation, confidence, explanation and sensor health.", [
    "https://sih-fit.vercel.app/problem/SIH26073",
    "https://github.com/jeevansai-hub/SIH-2026-/blob/main/ps_2026/README.md",
  ]);
}

// 3 — timeline based on Codex Grid slide-17 hierarchy.
{
  const s = deck.slides.add();
  header(s, "Nine phases turned a concept into evidence", "Delivery journey", 3);
  s.shapes.add({ geometry: "straightConnector1", position: { left: 70, top: 350, width: 1120, height: 0 }, fill: "none", line: { style: "solid", fill: C.ink, width: 2 } });
  const stages = [
    [100, "01–03", "Data & benchmark", "Verified source data, 13-fault library and 72 online-safe features."],
    [458, "04–06", "Models & safe repair", "Calibrated detection, weather protection, diagnosis, correction and health."],
    [816, "07–09", "Platform & delivery", "Streaming API, dashboard, genuine live feed, verification and SIH package."],
  ];
  stages.forEach(([x, label, titleValue, body], i) => {
    s.shapes.add({ geometry: "ellipse", position: { left: x, top: 340, width: 20, height: 20 }, fill: i === 2 ? C.green : C.blue, line: { style: "solid", fill: "none", width: 0 } });
    text(s, label, x, 294, 125, 28, 17, i === 2 ? C.green : C.blue, true);
    text(s, titleValue, x, 398, 300, 42, 25, C.ink, true);
    text(s, body, x, 448, 300, 120, 18, C.muted);
  });
  pill(s, "ALL PHASES COMPLETE", 960, 595, 230, C.paleGreen, C.green);
  notes(s, "Use this timeline to show that the project was built in dependency order: provenance first, models second, delivery last.");
}

// 4 — architecture.
{
  const s = deck.slides.add();
  header(s, "One pipeline serves offline proof and live operation", "System architecture", 4);
  const columns = [
    [42, "INPUT", ["NOAA benchmark", "Live METAR", "Replay scenarios"], C.paleBlue, C.blue],
    [306, "QUALITY", ["Schema + QC", "Temporal features", "Neighbour context"], C.paper, C.ink],
    [570, "DECISION", ["Fault probability", "Weather decision", "Root cause + abstain"], C.paleGreen, C.teal],
    [834, "ACTION", ["Correction + interval", "Health score", "Maintenance priority"], C.paleAmber, C.amber],
    [1098, "OUTPUT", ["Dashboard", "REST API", "CSV incident report"], C.paper, C.blue],
  ];
  columns.forEach(([x, label, items, fill, accent], i) => {
    const w = i === 4 ? 142 : 216;
    rect(s, x, 178, w, 352, fill, "rounded-2xl", "none");
    text(s, label, x + 18, 198, w - 36, 28, 14, accent, true);
    text(s, items.join("\n\n"), x + 18, 252, w - 36, 210, 18, C.ink, true);
    if (i < columns.length - 1) {
      text(s, "→", x + w + 10, 319, 28, 40, 30, C.blue, true, "center");
    }
  });
  text(s, "Frozen 2024 model policy", 488, 568, 300, 30, 17, C.red, true, "center");
  text(s, "No future leakage · explicit unknown outcome · corrections remain advisory", 340, 604, 600, 32, 17, C.muted, false, "center");
  notes(s, "Walk left to right. Both offline replay and live observations enter the same quality, feature and decision path. The frozen policy prevents demo-time threshold changes.");
}

// 5 — data evidence, using table-heavy slide-14 hierarchy.
{
  const s = deck.slides.add();
  header(s, "The benchmark is genuine, hashed and leakage-safe", "Data evidence", 5);
  text(s, "NOAA/NCEI Global Hourly ISD · India · 2022–2024", 42, 118, 900, 34, 20, C.muted);
  const values = [
    ["Evidence", "Value", "Validation"],
    ["Processed observations", "578,448", "Deduplicated"],
    ["Stations / clusters", "24 / 4", "Metadata checked"],
    ["Source files", "72 observations", "SHA-256 manifest"],
    ["Clean candidates", "98.4761%", "Range + quality screened"],
    ["Model split", "2022 / 2023 / 2024", "Train / select / locked test"],
    ["Unseen station holdout", "4 stations", "Never trained"],
    ["Fault library", "546 episodes", "13 classes + weather"],
  ];
  const t = s.tables.add({ rows: values.length, columns: 3, left: 42, top: 180, width: 1196, height: 412, values, columnWidths: [470, 250, 476] });
  t.styleOptions = { headerRow: true, bandedRows: true };
  t.borders.assign({ style: "solid", fill: C.line, width: 1 });
  for (let c = 0; c < 3; c++) {
    t.getCell(0, c).fill = C.ink;
    t.getCell(0, c).text.style = { fontSize: 17, bold: true, color: C.white };
  }
  for (let r = 1; r < values.length; r++) for (let c = 0; c < 3; c++) t.getCell(r, c).text.style = { fontSize: 16, color: C.ink };
  pill(s, "14/14 SOURCE CHECKS PASS", 42, 612, 258, C.paleGreen, C.green);
  notes(s, "This is the foundation of the credibility story. The fault labels are controlled injections, but the underlying meteorological observations and metadata are genuine official data.", [
    "https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database",
  ]);
}

// 6 — chart based on Codex Grid slide-20 chart/card hierarchy.
{
  const s = deck.slides.add();
  header(s, "The model catches episodes with low false-alarm pressure", "Locked 2024 results", 6);
  s.charts.add("bar", {
    position: { left: 42, top: 155, width: 700, height: 450 },
    categories: ["Precision", "Recall", "F1", "AUCPR", "Episode recall"],
    series: [
      { name: "Unseen time", values: [76.92, 39.82, 52.47, 46.77, 74.31], fill: C.blue },
      { name: "Unseen stations", values: [78.57, 44.00, 56.41, 51.83, 75.00], fill: C.teal },
    ],
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { fontSize: 14, fill: C.ink } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fontSize: 12, fill: C.ink, bold: true } },
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 58 },
    xAxis: { min: 0, max: 100, majorUnit: 20, numberFormatCode: "0\"%\"", majorGridlines: { style: "solid", fill: C.line, width: 1 }, textStyle: { fontSize: 12, fill: C.muted } },
    yAxis: { textStyle: { fontSize: 14, fill: C.ink }, line: { style: "solid", fill: C.line, width: 1 } },
    chartFill: C.white,
    chartLine: { style: "solid", fill: C.white, width: 0 },
    plotAreaFill: { type: "none" },
    plotAreaLine: { style: "solid", fill: C.white, width: 0 },
  });
  metricCard(s, 790, 155, 408, "Weather protection", "87.97% F1", "824 regional-weather rows · 1.699% fault FPR", C.paleGreen, C.teal);
  metricCard(s, 790, 307, 408, "Event decision", "99.19%", "Accuracy is contextual; use F1/AUCPR for faults", C.paleBlue, C.blue);
  metricCard(s, 790, 459, 408, "False alarms", "0.031/day", "Per station-day on unseen time", C.paleAmber, C.amber);
  notes(s, "Do not call 99.19% the model's only accuracy. Anomalies are rare, so present precision, recall, F1, AUCPR, false alarms and episode recall together.");
}

// 7 — correction and safety.
{
  const s = deck.slides.add();
  header(s, "Correction improved values—but automation stays gated", "Safe repair", 7);
  const cards = [
    [42, "TEMPERATURE", "1.66 °C", "corrected MAE", "85.64% error reduction", C.paleBlue, C.blue],
    [438, "PRESSURE", "1.56 hPa", "corrected MAE", "98.63% error reduction", C.paleGreen, C.teal],
    [834, "HUMIDITY", "12.92% RH", "corrected MAE", "57.86% error reduction", C.paleAmber, C.amber],
  ];
  cards.forEach(([x, label, value, sub, detail, fill, accent]) => {
    rect(s, x, 162, 360, 226, fill, "rounded-2xl", "none");
    text(s, label, x + 24, 184, 310, 28, 14, accent, true);
    text(s, value, x + 24, 228, 310, 54, 36, C.ink, true);
    text(s, sub, x + 24, 286, 310, 28, 17, C.muted);
    text(s, detail, x + 24, 334, 310, 28, 17, accent, true);
  });
  rect(s, 42, 432, 1152, 148, C.ink, "rounded-2xl", "none");
  text(s, "87", 72, 454, 128, 72, 50, C.white, true);
  text(s, "automatic temperature/pressure repairs", 205, 458, 500, 36, 24, C.white, true);
  text(s, "zero measured false corrections across both locked 2024 holdouts", 205, 500, 650, 34, 18, "#C7D2FE");
  pill(s, "HUMIDITY: REVIEW ONLY", 910, 476, 240, C.paleAmber, C.amber);
  text(s, "Coverage is limited by missed detection and affected-sensor inference; advisory output remains the default.", 42, 612, 1110, 34, 18, C.muted);
  notes(s, "This directly resolves the earlier limitation: we improved review coverage, calibrated uncertainty by split, and added strict automatic gates. We did not claim all corrections are safe to apply automatically.");
}

// 8 — live dashboard.
{
  const s = deck.slides.add();
  header(s, "Genuine live observations now use the same decision path", "Live operation", 8);
  const bytes = await fs.readFile(SCREENSHOT);
  s.images.add({
    blob: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    contentType: "image/png",
    alt: "SkyGuard live observation mode showing real METAR values",
    fit: "cover",
    position: { left: 42, top: 142, width: 820, height: 474 },
    geometry: "roundRect",
    borderRadius: "rounded-xl",
  });
  metricCard(s, 900, 152, 298, "Reporting", "12 / 14", "configured Indian stations", C.paleGreen, C.teal);
  metricCard(s, 900, 302, 298, "Snapshot", "400", "genuine observations", C.paleBlue, C.blue);
  metricCard(s, 900, 452, 298, "Refresh", "5 min", "optional dashboard schedule", C.paleAmber, C.amber);
  text(s, "Reported: temperature + QNH pressure · Derived: relative humidity", 42, 628, 900, 30, 17, C.muted);
  notes(s, "Switch the live mode on during the demo. Be precise: the feed is genuine METAR terminal data. Humidity is derived from temperature and dew point. Live alerts are signals; benchmark accuracy comes from the locked labelled tests.", [
    "https://connect.aviationweather.gov/data/api/",
  ]);
}

// 9 — compliance table.
{
  const s = deck.slides.add();
  header(s, "Every mandatory software output is demonstrated", "SIH compliance", 9);
  const values = [
    ["Statement requirement", "SkyGuard implementation", "Status"],
    ["Real-time anomaly detection", "Streaming engine + live refresh + cache", "Complete"],
    ["Faults and communication errors", "13-class benchmark + stateful QC", "Complete"],
    ["Temporal / seasonal learning", "Causal rolling, EWMA and seasonal features", "Complete"],
    ["Multivariate consistency", "Cross-sensor and calibrated event model", "Complete"],
    ["Weather vs sensor failure", "Neighbour agreement + regional scenario", "Complete"],
    ["Confidence and explanation", "Calibration, abstention, evidence text", "Complete"],
    ["Health and maintenance", "Sensor score, priority and action", "Complete"],
    ["Correction / imputation", "Uncertainty-aware advisory correction", "Optional done"],
    ["Dashboard and deployability", "Offline/local web UI, API and report export", "Complete"],
  ];
  const t = s.tables.add({ rows: values.length, columns: 3, left: 42, top: 145, width: 1196, height: 470, values, columnWidths: [350, 636, 210] });
  t.styleOptions = { headerRow: true, bandedRows: true };
  t.borders.assign({ style: "solid", fill: C.line, width: 1 });
  for (let c = 0; c < 3; c++) {
    t.getCell(0, c).fill = C.ink;
    t.getCell(0, c).text.style = { fontSize: 16, bold: true, color: C.white };
  }
  for (let r = 1; r < values.length; r++) {
    t.getCell(r, 0).text.style = { fontSize: 14, bold: true, color: C.ink };
    t.getCell(r, 1).text.style = { fontSize: 14, color: C.ink };
    t.getCell(r, 2).fill = r === 8 ? C.paleAmber : C.paleGreen;
    t.getCell(r, 2).text.style = { fontSize: 14, bold: true, color: r === 8 ? C.amber : C.green };
  }
  text(s, "Production gap: replace the public METAR adapter with the official IMD AWS endpoint and validate on confirmed field faults.", 42, 630, 1140, 32, 17, C.red, true);
  notes(s, "This is the honest compliance answer: complete for the SIH software prototype, not yet an operational IMD deployment. Hardware is not required for this team-constrained solution.", [
    "https://sih-fit.vercel.app/problem/SIH26073",
  ]);
}

// 10 — close.
{
  const s = deck.slides.add();
  s.background.fill = C.ink;
  pill(s, "READY FOR SIH DEMONSTRATION", 42, 42, 286, "#173A5E", "#8DD9FF");
  text(s, "Trust every weather reading.", 42, 140, 740, 90, 51, C.white, true);
  text(s, "SkyGuard detects, distinguishes, diagnoses, explains, corrects safely and prioritizes maintenance—live or fully offline.", 42, 242, 760, 120, 25, "#CBD5E1");
  rect(s, 866, 118, 328, 362, "#172033", "rounded-2xl", "#334155");
  text(s, "FINAL PROOF", 896, 148, 265, 28, 14, "#7DD3FC", true);
  text(s, "51", 896, 198, 120, 60, 48, C.white, true);
  text(s, "automated tests pass", 896, 257, 250, 28, 18, "#CBD5E1");
  text(s, "14 / 14", 896, 322, 180, 52, 38, C.white, true);
  text(s, "final delivery checks", 896, 374, 250, 28, 18, "#CBD5E1");
  pill(s, "PHASES 0–9 COMPLETE", 896, 424, 245, C.paleGreen, C.green);
  text(s, "Next pilot step", 42, 506, 220, 28, 17, "#7DD3FC", true);
  text(s, "Connect the official IMD AWS stream and collect confirmed maintenance labels for operational acceptance.", 42, 548, 760, 80, 24, C.white, true);
  text(s, "SkyGuard AI · SIH 26073", 42, 660, 420, 24, 14, "#94A3B8");
  notes(s, "Close on the outcome and ask judges to test both scenarios: one-station drift and regional weather. Then show the live feed. Do not overclaim production readiness.");
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

await fs.mkdir(RENDER, { recursive: true });
for (const [index, slide] of deck.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(path.join(RENDER, `${stem}.png`), await deck.export({ slide, format: "png", scale: 1 }));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(RENDER, `${stem}.layout.json`), await layout.text());
}
await writeBlob(path.join(RENDER, "montage.webp"), await deck.export({ format: "webp", montage: { columns: 2, width: 1200, padding: 20, gap: 16, background: C.paper }, scale: 1 }));
const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(path.join(OUT, "SkyGuard_AI_SIH26073_Final.pptx"));
console.log(JSON.stringify({ slides: deck.slides.items.length, output: path.join(OUT, "SkyGuard_AI_SIH26073_Final.pptx") }, null, 2));
