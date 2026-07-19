"""
Recalculate distances from edited XLSX + create multi-sheet output.
"""

import pandas as pd
import geopandas as gpd
from shapely import Point
from pathlib import Path
import time

BASE = Path(r"C:\Users\pirate-1\Documents\06_Sistem_dan_Development\repos\PetaJalanProvinsi")

ROADS_PARQUET = BASE / "ruas_jalan.parquet"
INPUT_XLSX = BASE / "sekolah_matched.xlsx"
OUTPUT_XLSX = BASE / "sekolah_matched.xlsx"

THRESHOLDS = [50, 60, 100, 150, 200]

print("=" * 60)
print("RECALCULATE DISTANCES + MULTI-SHEET XLSX")
print("=" * 60)

# Load roads
print("Loading roads...")
roads = gpd.read_parquet(ROADS_PARQUET)
roads_utm = roads.to_crs("EPSG:32748")
roads_index = roads.sindex
print(f"  {len(roads)} road segments")

# Load edited XLSX
print("Loading edited XLSX...")
df = pd.read_excel(INPUT_XLSX, sheet_name="matched_schools")
print(f"  {len(df)} schools")

# Parse coordinates
df["LINTANG"] = pd.to_numeric(df["LINTANG"], errors="coerce")
df["BUJUR"] = pd.to_numeric(df["BUJUR"], errors="coerce")
valid = df["LINTANG"].notna() & df["BUJUR"].notna()
print(f"  Valid coordinates: {valid.sum()}")

# Create geometry
geometry = [Point(lon, lat) for lat, lon in zip(df["LINTANG"], df["BUJUR"])]
schools = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
schools_utm = schools.to_crs("EPSG:32748")

# Match each school to nearest road
print("Matching schools to roads...")
start = time.time()
n = len(schools)

results = {
    "nearest_road_name": [], "nearest_road_kode": [], "nearest_road_id": [],
    "nearest_road_panjang_km": [], "nearest_road_unit_kerja": [], "nearest_road_lokasi_kode": [],
    "distance_m": [],
}

for idx in range(n):
    pt_utm = schools_utm.geometry.iloc[idx]
    pt_wgs = schools.geometry.iloc[idx]

    # Spatial index query
    bounds = pt_wgs.buffer(0.01).bounds
    candidates = list(roads_index.intersection(bounds))
    if not candidates:
        bounds = pt_wgs.buffer(0.05).bounds
        candidates = list(roads_index.intersection(bounds))

    if not candidates:
        for k in results: results[k].append(None)
        continue

    min_dist = float("inf")
    best = None
    for cidx in candidates:
        d = pt_utm.distance(roads_utm.geometry.iloc[cidx])
        if d < min_dist:
            min_dist = d
            best = cidx

    road = roads.iloc[best]
    results["nearest_road_name"].append(road.get("nama", None))
    results["nearest_road_kode"].append(road.get("kode_number", None))
    results["nearest_road_id"].append(road.get("id", None))
    results["nearest_road_panjang_km"].append(road.get("panjang_km", None))
    results["nearest_road_unit_kerja"].append(road.get("unit_kerja_kode", None))
    results["nearest_road_lokasi_kode"].append(road.get("lokasi_kode", None))
    results["distance_m"].append(round(min_dist, 2))

    if (idx + 1) % 5000 == 0:
        elapsed = time.time() - start
        rate = (idx + 1) / elapsed
        eta = (n - idx - 1) / rate
        print(f"  {idx+1}/{n} ({rate:.0f}/s, ETA {eta:.0f}s)")

elapsed = time.time() - start
print(f"  Done in {elapsed:.1f}s")

# Update dataframe
for col, vals in results.items():
    df[col] = vals

# Add threshold booleans
for t in THRESHOLDS:
    col = f"within_{t}m"
    df[col] = df["distance_m"].apply(lambda d: bool(d is not None and d <= t) if pd.notna(d) else False)
    count = df[col].sum()
    print(f"  {col}: {count}")

# === CREATE MULTI-SHEET XLSX ===
print("\nCreating multi-sheet XLSX...")

# Drop geometry column if present
if "geometry" in df.columns:
    df = df.drop(columns=["geometry"])

# Define sheets
JENJANG_MAP = {
    "SD": "SD",
    "SMP": "SMP",
    "SMA": "SMA",
    "SMK": "SMK",
    "SLB": "SLB",
}

sheets = {
    "DATA": df,
    "SD": df[df["Jenjang"] == "SD"],
    "SMP": df[df["Jenjang"] == "SMP"],
    "SMA": df[df["Jenjang"] == "SMA"],
    "SMK": df[df["Jenjang"] == "SMK"],
    "SLB": df[df["Jenjang"] == "SLB"],
}

# REKAP: schools within 60m, grouped by Jenjang x Kabupaten
rekap_df = df[df["within_60m"] == True].copy()
rekap = rekap_df.groupby(["Jenjang", "KABUPATEN"]).agg(
    jumlah_sekolah=("NAMA SEKOLAH", "count"),
    rata_jarak=("distance_m", "mean"),
    min_jarak=("distance_m", "min"),
    max_jarak=("distance_m", "max"),
).reset_index()
rekap["rata_jarak"] = rekap["rata_jarak"].round(2)

# Add total row
total_row = pd.DataFrame([{
    "Jenjang": "TOTAL",
    "KABUPATEN": "",
    "jumlah_sekolah": rekap["jumlah_sekolah"].sum(),
    "rata_jarak": rekap["rata_jarak"].mean().round(2),
    "min_jarak": rekap["min_jarak"].min(),
    "max_jarak": rekap["max_jarak"].max(),
}])
rekap = pd.concat([rekap, total_row], ignore_index=True)

sheets["REKAP"] = rekap

# Write XLSX
with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
    for sheet_name, sheet_df in sheets.items():
        sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"  {sheet_name}: {len(sheet_df)} rows")

print(f"\nSaved: {OUTPUT_XLSX}")
print("=" * 60)
print("DONE")
