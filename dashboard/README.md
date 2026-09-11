# Dashboard

The Phase 9 live/offline judge dashboard is complete.

- `index.html` defines the complete non-technical command-centre experience.
- `styles.css` provides the responsive offline visual system.
- `app.js` connects live/offline mode, replay controls, station health, readings, incidents, corrections, metrics, and downloads to the local FastAPI service.

Double-click `start_skyguard.bat` or start `python src/data/run_api.py` from the project root, then open `http://127.0.0.1:8000/`. Developer API documentation remains available at `/docs`.

Offline Replay is the deterministic no-internet judge mode. Live Observations refreshes genuine AviationWeather.gov METAR data and retains the last verified snapshot if connectivity fails.
