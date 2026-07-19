"""
Match schools to nearest provincial road segments.
Outputs: GeoParquet (roads + matched schools) and XLSX with distance thresholds.
"""

import pandas as pd
import geopandas as gpd
from shapely import from_wkb, Point
from shapely.ops import nearest_points
import numpy as np
from pathlib import Path
import time

# === CONFIG ===
BASE_DIR = Path(r"C:\Users\pirate-1\Documents\06_Sistem_dan_Development\repos\PetaJalanProvinsi")
ROADS_CSV = BASE_DIR / "ruas_jalan_rows (4).csv"
SCHOOLS_XLSX = BASE_DIR / "DATA_Sekolah_di_Jalan_provinsi.xlsx"
OUTPUT_ROADS_PARQUET = BASE_DIR / "ruas_jalan.parquet"
OUTPUT_SCHOOLS_PARQUET = BASE_DIR / "sekolah_matched.parquet"
OUTPUT_SCHOOLS_XLSX = BASE_DIR / "sekolah_matched.xlsx"

# Distance thresholds in meters
THRESHOLDS = [50, 100, 150, 200]


def load_roads(csv_path: Path) -> gpd.GeoDataFrame:
    """Load road segments from CSV and parse EWKB geometry."""
    print(f"Loading roads from {csv_path}...")
    df = pd.read_csv(csv_path, dtype=str)
    print(f"  Raw rows: {len(df)}")

    # Parse hex WKB geometry
    df["geom_hex"] = df["geom"].str.strip()
    geometry = df["geom_hex"].apply(lambda h: from_wkb(bytes.fromhex(h)))

    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf = gdf.drop(columns=["geom", "geom_hex"])

    # Ensure numeric types
    gdf["panjang_km"] = pd.to_numeric(gdf["panjang_km"], errors="coerce")

    print(f"  Parsed road segments: {len(gdf)}")
    return gdf


def load_schools(xlsx_path: Path) -> gpd.GeoDataFrame:
    """Load schools from XLSX and create Point geometries from lat/lng."""
    print(f"Loading schools from {xlsx_path}...")
    df = pd.read_excel(xlsx_path, sheet_name="data", dtype=str)
    print(f"  Raw rows: {len(df)}")

    # Parse coordinates
    df["LINTANG"] = pd.to_numeric(df["LINTANG"], errors="coerce")
    df["BUJUR"] = pd.to_numeric(df["BUJUR"], errors="coerce")

    # Drop rows with invalid coordinates
    valid = df["LINTANG"].notna() & df["BUJUR"].notna()
    print(f"  Valid coordinates: {valid.sum()} / {len(df)}")

    df = df[valid].copy()
    geometry = [Point(lon, lat) for lat, lon in zip(df["LINTANG"], df["BUJUR"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    print(f"  Schools with valid geometry: {len(gdf)}")
    return gdf


def match_schools_to_roads(
    schools: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame,
    thresholds: list[int],
) -> gpd.GeoDataFrame:
    """
    For each school, find the nearest road segment and calculate distance.
    Uses spatial index (R-tree) for efficient nearest-neighbor search.
    """
    print("Building spatial index for roads...")
    roads_index = roads.sindex

    # Project to UTM Zone 48S (EPSG:32748) for accurate meter distances
    # West Java spans ~106-115°E → UTM 48S is appropriate
    roads_utm = roads.to_crs("EPSG:32748")
    schools_utm = schools.to_crs("EPSG:32748")

    n_schools = len(schools)
    results = {
        "nearest_road_name": [],
        "nearest_road_kode": [],
        "nearest_road_id": [],
        "nearest_road_panjang_km": [],
        "nearest_road_unit_kerja": [],
        "nearest_road_lokasi_kode": [],
        "distance_m": [],
    }

    print(f"Matching {n_schools} schools to nearest road...")
    start = time.time()

    for idx in range(n_schools):
        school_point_utm = schools_utm.geometry.iloc[idx]
        school_point_wgs = schools.geometry.iloc[idx]

        # Query spatial index for bounding box candidates
        # Use a generous buffer (0.01 degrees ~ 1km) to catch nearby roads
        bounds = school_point_wgs.buffer(0.01).bounds
        candidate_idx = list(roads_index.intersection(bounds))

        if not candidate_idx:
            # Fallback: search with larger buffer
            bounds = school_point_wgs.buffer(0.05).bounds
            candidate_idx = list(roads_index.intersection(bounds))

        if not candidate_idx:
            # No road found within 5km - mark as unmatched
            results["nearest_road_name"].append(None)
            results["nearest_road_kode"].append(None)
            results["nearest_road_id"].append(None)
            results["nearest_road_panjang_km"].append(None)
            results["nearest_road_unit_kerja"].append(None)
            results["nearest_road_lokasi_kode"].append(None)
            results["distance_m"].append(None)
            continue

        # Find nearest among candidates
        min_dist = float("inf")
        best_idx = None

        for cidx in candidate_idx:
            road_geom = roads_utm.geometry.iloc[cidx]
            dist = school_point_utm.distance(road_geom)
            if dist < min_dist:
                min_dist = dist
                best_idx = cidx

        # Get the road info
        road = roads.iloc[best_idx]
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
            eta = (n_schools - idx - 1) / rate
            print(f"  {idx+1}/{n_schools} ({rate:.0f}/s, ETA {eta:.0f}s)")

    elapsed = time.time() - start
    print(f"  Done in {elapsed:.1f}s ({n_schools/elapsed:.0f} schools/s)")

    # Add results to schools GeoDataFrame
    schools = schools.copy()
    for col, vals in results.items():
        schools[col] = vals

    # Add distance thresholds as booleans
    for t in thresholds:
        col_name = f"within_{t}m"
        schools[col_name] = schools["distance_m"].apply(
            lambda d: bool(d is not None and d <= t) if pd.notna(d) else False
        )
        count = schools[col_name].sum()
        print(f"  {col_name}: {count} schools")

    return schools


def save_outputs(
    roads: gpd.GeoDataFrame,
    schools: gpd.GeoDataFrame,
    roads_parquet: Path,
    schools_parquet: Path,
    schools_xlsx: Path,
):
    """Save all outputs."""
    # Save roads as GeoParquet
    print(f"Saving roads to {roads_parquet}...")
    roads.to_parquet(roads_parquet, index=False)
    print(f"  {len(roads)} road segments saved")

    # Save matched schools as GeoParquet
    print(f"Saving schools to {schools_parquet}...")
    schools.to_parquet(schools_parquet, index=False)
    print(f"  {len(schools)} schools saved")

    # Save matched schools as XLSX
    print(f"Saving schools to {schools_xlsx}...")
    # For XLSX, convert geometry to lat/lng columns (keep original + add matched data)
    xlsx_df = schools.drop(columns=["geometry"], errors="ignore")
    xlsx_df.to_excel(schools_xlsx, index=False, sheet_name="matched_schools")
    print(f"  {len(xlsx_df)} rows saved to XLSX")


def main():
    print("=" * 60)
    print("SCHOOL-TO-ROAD SPATIAL MATCHING")
    print("=" * 60)

    # Load data
    roads = load_roads(ROADS_CSV)
    schools = load_schools(SCHOOLS_XLSX)

    # Match
    matched = match_schools_to_roads(schools, roads, THRESHOLDS)

    # Save
    save_outputs(roads, matched, OUTPUT_ROADS_PARQUET, OUTPUT_SCHOOLS_PARQUET, OUTPUT_SCHOOLS_XLSX)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total roads:     {len(roads)}")
    print(f"Total schools:   {len(matched)}")
    matched_count = matched["nearest_road_kode"].notna().sum()
    print(f"Matched:         {matched_count} ({matched_count/len(matched)*100:.1f}%)")
    unmatched = len(matched) - matched_count
    print(f"Unmatched:       {unmatched}")
    print(f"\nDistance stats (matched only):")
    dist = matched["distance_m"].dropna()
    print(f"  Mean:   {dist.mean():.1f}m")
    print(f"  Median: {dist.median():.1f}m")
    print(f"  Min:    {dist.min():.1f}m")
    print(f"  Max:    {dist.max():.1f}m")
    print(f"  Std:    {dist.std():.1f}m")


if __name__ == "__main__":
    main()
