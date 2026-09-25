# SkyGuard AI - technical-approach slide notes

The compact diagram is designed for the **right half of a 16:9 SIH slide**. Insert the SVG for crisp Canva/PowerPoint scaling; use the PNG if SVG import is unavailable.

## What the arrows mean

1. **Two different input types.** IMD WIS2 and METAR provide direct station reports. Open-Meteo supplies weather-model estimates at map coordinates, not sensor measurements. The 1,008-point catalog includes synthetic or curated locations, so do not label it "1,008 verified live IMD AWS sensors."
2. **Trust and time alignment.** The pipeline records source identity, observation time, pressure meaning, relative-humidity origin, and missing or late reports. Past-only features avoid looking into the future.
3. **Three evidence streams.** Temporal and spatial physical checks support operational QC. LightGBM and causal TCN/GRU were built/evaluated in offline research on injected faults; the dashed border/arrow marks this lane as **advisory research**, not independently certified live performance.
4. **Safe decision.** Corroborated regional changes should be treated as possible weather events; isolated, persistent discrepancies become probable sensor-fault candidates; missing history or peers should trigger an insufficient-context state.
5. **Human-facing result.** FastAPI/Next.js provide the station map, alerts, possible root cause, sensor health and optional correction proposals. Raw reported values should not be overwritten automatically.

## Evidence and honest claims for the presenter

- `src/skyguard/providers/imd_wis2.py`, `src/skyguard/providers/metar.py`: observation adapters.
- `src/skyguard/providers/reference_weather.py`: Open-Meteo is correctly typed as a model reference in this adapter. **Caution:** `src/skyguard/ingestion/open_meteo.py` and parts of the current website still mislabel model estimates as direct AWS readings. Do not make that claim in the presentation.
- `src/skyguard/operational/qc.py`, `src/skyguard/spatial/buddy_check.py`: physical, temporal and neighbour QC; the operational evidence score is not a calibrated field fault probability.
- `reports/phase10_final.json`: offline Phase 10 baseline using three meteorological parameters and historical injected faults.
- `reports/iteration12_neural_honest/result_block.json`: empirical TCN/GRU challenger, **not promoted**. On the 2024 time holdout, point precision was 78.5%, point recall 27.3%; episode recall was 49.3%. The source was 24 NOAA/NCEI Indian proxy stations with injected fault labels, not IMD maintenance-confirmed AWS faults.
- `src/skyguard/models/deep_ensemble.py` and `tools/run_genuine_ml_inference.py` exist, but the latter invokes the detector with an **empty 24-hour history** and the neural weights are trained on generated diurnal sequences. Its resulting 1,008-point score is not an independently validated live fault probability. The diagram therefore does **not** present it as a certified production neural engine.
- `reports/iteration14_1008_aws_live_benchmark.json` reports 97.3% recall from a simple simulated fault experiment, not real field labels; it should not appear as live-model accuracy.

## Suggested 20-second narration

"SkyGuard direct station observations ko Open-Meteo weather-model reference se alag rakhta hai. Pehle source, time aur pressure/RH semantics verify hote hain. Phir past-only temporal checks, nearby-station comparison aur research ML evidence milkar anomaly candidate banate hain. Weather-coherence veto real regional event ko sensor fault bolne se bachata hai. Dashboard root cause, health aur advisory correction dikhata hai; raw reading ko automatically replace nahi karta. Field-verified fault recall abhi available nahi hai."
