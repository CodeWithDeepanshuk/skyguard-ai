# SkyGuard AI — Official IMD AWS Cutover Runbook

## Sabse important decision

IMD AWS API ko browser, Next.js client ya Vercel frontend se direct call nahi karna hai. API key ek static public server IP se bind hoti hai aur request ko API key ke saath short-lived JWT bhi chahiye. Isliye flow hoga:

`IMD AWS API -> fixed-IP private collector -> durable database -> SkyGuard QC/ML -> public website`

Raw IMD response public GitHub/Vercel bundle mein publish nahi hoga. Website authorized, derived operational output dikhayegi aur IMD attribution/terms follow karegi.

## 1. Keys ka sahi allocation

- Abhi sirf **DEV key 1** banayein: `skyguard-imd-dev-collector`.
- DEV key 2 ko rotation/emergency ke liye unused rakhein.
- Production collector final hone par **PROD key 1** banayein.
- PROD key 2 ko rotation/emergency ke liye unused rakhein.
- Key banate waqt public IP wahi dalein jo collector machine par `https://api.imd.gov.in/public/ip.php` kholne par aaye.
- Dynamic home IP, Vercel function IP ya unverified shared-host IP ko production key se bind na karein.

## 2. Secret configuration

Collector server ke secret manager/environment mein ye values rakhein:

```text
IMD_API_KEY=<dev key>
IMD_API_EMAIL=<registered portal email>
IMD_API_PASSWORD=<portal password>
DATABASE_URL=<durable PostgreSQL URL>
```

`IMD_API_JWT_TOKEN` sirf short manual test ke liye optional hai. Production backend email/password se token endpoint call karta hai, token ko memory mein cache karta hai, aur expiry se pehle renew karta hai.

In values ko `.env.example`, GitHub, screenshot, browser JavaScript, Vercel public environment variable ya chat mein paste na karein.

## 3. First authenticated download-and-inspection test

PowerShell mein repository root se, secrets current process mein set karke:

```powershell
$env:IMD_API_KEY = "YOUR_DEV_KEY"
$env:IMD_API_EMAIL = "YOUR_REGISTERED_EMAIL"
$env:IMD_API_PASSWORD = "YOUR_PASSWORD"
python tools/download_imd_aws_for_inspection.py
```

Ye command dono documented endpoints download karti hai, exact raw response ko private gitignored archive mein rakhti hai, SHA-256 receipt banati hai aur values ke bina structural/schema report banati hai. Is stage par koi row observation declare, normalize ya model mein ingest nahi hoti.

Expected result: dono endpoints ke liye `accepted_for_schema_review`. `401` ka matlab API key/JWT/user pair ya source IP mismatch ho sakta hai. Application-error envelope, malformed JSON ya unexpected content type par normalization/model training start nahi karni hai.

Sanitized `*.shape.json` aur `*.receipt.json` review karein. Raw `*.json` public GitHub, PPT ya chat mein upload na karein. Real payload aur endpoint-specific reference agree hone ke baad hi `IMD_NORMALIZATION_ENABLED=true` ki approval di jayegi.

## 4. Purane data ko safely OLD mark/archive karna

Replacement se pehle dry-run:

```powershell
python tools/archive_legacy_pre_imd.py
```

Pehla genuine IMD ingestion successful hone ke baad:

```powershell
python tools/archive_legacy_pre_imd.py --apply
```

Script allowlisted legacy catalog/snapshot files ki checksummed **copy** `data/archive/pre_imd_api_<UTC timestamp>/` mein rakhta hai. Originals abhi delete/move nahi hote, isliye website cutover ke beech break nahi hoti. Final cutover ke baad old sources ko UI/API selection se disable karna alag controlled change hoga.

## 5. Candidate fields - real schema verification ke baad hi final

Public endpoint reference ke basis par candidate SIH 26073 inputs neeche hain, lekin real sanitized response se names, units, missing codes aur semantics verify karna mandatory hai:

- `CURR_TEMP` -> temperature °C
- `MSLP` -> mean-sea-level pressure hPa
- `RH` -> relative humidity %

Identity/spatial/temporal metadata:

- `CALL_SIGN`, `ID`, `STATION`, `STATE`, `DISTRICT`
- `DATE`, `TIME`
- `Latitude`, `Longitude`

Wind, rain, weather code, dew point etc. raw audit mein preserve ho sakte hain, lekin primary anomaly model ko SIH scope ke bahar silently expand nahi karenge. Open-Meteo ko AWS observation nahi bolenge; woh sirf independent reference/NWP baseline ho sakta hai.

## 6. Collection cadence aur storage

- Abhi collector ko scheduled loop mein mat chalayein. Pehle portal/API support se documented request limit aur permissible cadence confirm karein; phir `IMD_API_MIN_INTERVAL_SECONDS` explicitly configure karein.
- Har snapshot append-only rahe; `(provider, station, timestamp)` par deduplicate ho.
- Raw JSON/private payload hash audit ke liye store ho.
- Normalized database mein only validated direct observations operational inference ko milein.
- Mapping endpoint daily ya station metadata change par refresh ho; har 15 minute nahi.
- PostgreSQL use karein. Ephemeral host filesystem ko historical training store na samjhein.

## 7. Model kab train hoga

Live API access milte hi supervised model ko train kar dena scientifically galat hoga, kyunki current readings ke paas verified `fault/healthy` labels nahi hain.

- Day 0–1: schema, time zone, station IDs, units, missingness aur cadence validate.
- Day 2–7: causal QC rules, duplicate/freeze/gap monitoring aur spatial-neighbour graph smoke test.
- Day 30+: first pilot baseline on genuine history; evaluation copy par documented injected freeze/spike/drift/bias faults; station-disjoint + future-time holdout.
- Day 60–90+: season/region robustness, calibration and drift review.
- Real precision/recall claim: maintenance logs or independently verified IMD fault labels milne ke baad hi.

Recommended ensemble remains: physical/range QC + temporal persistence/CUSUM + spatial buddy residual + calibrated tree model. Neural TCN/autoencoder tabhi promote hoga jab same locked holdout par simpler baseline ko consistently beat kare.

## 8. Website cutover gate

Website par `Official IMD AWS` tab tabhi primary source bane jab:

1. latest successful ingestion recent ho;
2. national mapping loaded ho;
3. timestamp and units confirmed ho;
4. enough station history available ho;
5. model version and calibration receipt available ho.

Tab tak current page ko `data collection / research mode` clearly dikhana chahiye—unverified probability ko production accuracy nahi bolna hai.
