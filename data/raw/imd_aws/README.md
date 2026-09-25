# IMD AWS Raw Observation Store

## Provenance & Storage Contract
1. **Source**: Authenticated IMD AWS API (`POST /api/oauth/token.php` -> `GET /api/v1/aws_data`).
2. **Immutability**: Raw JSON responses are written directly to this directory before any normalization, filtering, or parsing.
3. **Audit Trail**: Every snapshot file has an accompanying `.receipt.json` containing:
   - Request timestamp (UTC)
   - Source URL & HTTP status
   - Raw payload SHA-256 hash
   - Exact byte count
   - Zero synthetic rows confirmation (`generated_rows: 0`)
4. **Parameter Scope**: Only the three official SIH 26073 parameters are ingested:
   - Air Temperature (°C)
   - Atmospheric / Sea-Level Pressure (hPa)
   - Relative Humidity (%)
5. **No Silent Fallback**: If the official IMD API is offline or returns an error, the system must never synthesize readings or substitute forecast models into observation storage.
