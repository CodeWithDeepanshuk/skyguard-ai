"""Build the All-India AWS Station Network Catalog from official metadata."""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METADATA_FILE = ROOT / "data" / "raw" / "metadata" / "isd-history.csv"
OUTPUT_FILE = ROOT / "config" / "all_india_aws_network.csv"

def assign_climate_zone(lat, lon, elev):
    if pd.isna(lat) or pd.isna(lon):
        return "Unknown"
    # Island territories
    if (lat < 14 and lon > 92) or (lat < 12 and lon < 74):
        return "Island Territories"
    # Northeast Hills
    if lon > 88 and lat > 21.5:
        return "Northeast Hills"
    # Northern Himalayas
    if lat >= 30 or (lat >= 29 and elev > 1000):
        return "Northern Himalayas"
    # Coastal Plains
    if (lon > 82 and lat < 21) or (lon < 73.5 and lat < 21) or (lat < 12):
        return "Coastal Plains"
    # Western Arid / Semi-Arid
    if lon < 76 and lat >= 22 and lat < 30:
        return "Western Arid/Semi-Arid"
    # Indo-Gangetic Plains
    if lat >= 24 and lat < 30 and lon >= 76 and lon <= 88:
        return "Indo-Gangetic Plains"
    # Deccan Plateau / South Interior
    if lat < 20 and lat >= 12 and lon >= 74 and lon <= 80:
        return "Deccan Plateau"
    # Central Plateau
    return "Central Plateau"

def main():
    print("Reading ISD history...")
    df = pd.read_csv(METADATA_FILE)
    in_stations = df[df["CTRY"] == "IN"].copy()
    
    # Active in modern era (reporting into 2020s)
    in_stations["BEGIN"] = in_stations["BEGIN"].astype(str)
    in_stations["END"] = in_stations["END"].astype(str)
    
    # Standardize columns
    in_stations["station_id"] = in_stations["USAF"].astype(str).str.zfill(6) + in_stations["WBAN"].astype(str).str.zfill(5)
    in_stations["station_name"] = in_stations["STATION NAME"].fillna("UNKNOWN").str.title()
    in_stations["latitude"] = pd.to_numeric(in_stations["LAT"], errors="coerce")
    in_stations["longitude"] = pd.to_numeric(in_stations["LON"], errors="coerce")
    in_stations["elevation_m"] = pd.to_numeric(in_stations["ELEV(M)"], errors="coerce").fillna(0.0)
    in_stations["icao"] = in_stations["ICAO"].fillna("").astype(str).str.strip().str.upper()
    
    # Filter out entries without coordinates (e.g. placeholder/bogus entries)
    in_stations = in_stations[in_stations["latitude"].notna() & in_stations["longitude"].notna()].copy()
    
    # Active status
    in_stations["is_active_2024_plus"] = (in_stations["END"] >= "20240101").astype(int)
    in_stations["is_active_2020_plus"] = (in_stations["END"] >= "20200101").astype(int)
    
    # Assign climate zone
    in_stations["climate_zone"] = [
        assign_climate_zone(row["latitude"], row["longitude"], row["elevation_m"])
        for _, row in in_stations.iterrows()
    ]
    
    # Load 24 benchmark stations if available
    benchmark_file = ROOT / "config" / "stations.csv"
    bench_map = {}
    if benchmark_file.exists():
        bench_df = pd.read_csv(benchmark_file)
        for _, r in bench_df.iterrows():
            bench_map[str(r["station_id"])] = {
                "cluster": r.get("cluster", ""),
                "evaluation_role": r.get("evaluation_role", ""),
                "icao": str(r.get("icao", "")).strip() if pd.notna(r.get("icao")) else "",
            }
            
    clusters = []
    roles = []
    is_bench = []
    icaos = []
    
    for _, row in in_stations.iterrows():
        sid = str(row["station_id"])
        if sid in bench_map:
            clusters.append(bench_map[sid]["cluster"])
            roles.append(bench_map[sid]["evaluation_role"])
            is_bench.append(1)
            icaos.append(bench_map[sid]["icao"] or row["icao"])
        else:
            clusters.append(row["climate_zone"].lower().replace(" ", "_").replace("/", "_").replace("-", "_"))
            roles.append("all_india_network")
            is_bench.append(0)
            icaos.append(row["icao"])
            
    in_stations["cluster"] = clusters
    in_stations["evaluation_role"] = roles
    in_stations["is_benchmark"] = is_bench
    in_stations["icao"] = icaos
    
    # Sort by active status, benchmark status, climate zone, and station name
    in_stations = in_stations.sort_values(
        by=["is_benchmark", "is_active_2024_plus", "climate_zone", "station_name"],
        ascending=[False, False, True, True]
    )
    
    cols = [
        "station_id", "station_name", "climate_zone", "cluster", "evaluation_role",
        "latitude", "longitude", "elevation_m", "icao", "is_benchmark",
        "is_active_2024_plus", "is_active_2020_plus", "BEGIN", "END"
    ]
    catalog = in_stations[cols].copy()
    catalog.to_csv(OUTPUT_FILE, index=False)
    
    print(f"All-India AWS Catalog written to {OUTPUT_FILE}")
    print(f"Total Indian stations: {len(catalog)}")
    print(f"Benchmark stations: {catalog['is_benchmark'].sum()}")
    print(f"Active 2024+: {catalog['is_active_2024_plus'].sum()}")
    print(f"Stations with ICAO: {(catalog['icao'] != '').sum()}")
    print("\nBreakdown by Climate Zone:")
    print(catalog[catalog["is_active_2020_plus"] == 1]["climate_zone"].value_counts())

if __name__ == "__main__":
    main()
