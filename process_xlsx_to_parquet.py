import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq
import struct

def lonlat_to_wkb(lon, lat):
    """Create WKB Point from lon/lat (little-endian, no SRID)."""
    return struct.pack('<BIdd', 1, 1, lon, lat)

# Read new xlsx
wb = openpyxl.load_workbook(
    r'C:\Users\pirate-1\Documents\2. Sistem dan Development\3. Repos\PetaSekolahJalanProvinsi'
    r'\yang perlu di cek - Data Sekolah JawaBarat Dekat Jalan Provinsi (1).xlsx',
    read_only=True
)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
wb.close()

data_rows = rows[1:]
print(f"Read {len(data_rows)} rows from xlsx")

# Column indices in the new xlsx
COL = {
    'Jenjang': 0, 'Status': 1, 'NAMA SEKOLAH': 2, 'NPSN': 3, 'BENTUK': 4,
    'NAMA DUSUN': 5, 'DESA/KELURAHAN': 6, 'KECAMATAN': 7, 'KABUPATEN': 8,
    'PROVINSI': 9, 'KODE POS': 10, 'LINTANG': 11, 'BUJUR': 12,
    'STATUS': 13, 'AKREDITASI': 14, 'SUMBER LISTRIK': 15, 'AKSES INTERNET': 16,
    'SUMBER AIR': 17, 'KECUKUPAN AIR': 18,
    'nearest_road_name': 19, 'nearest_road_kode': 20, 'nearest_road_id': 21,
    'nearest_road_panjang_km': 22, 'nearest_road_unit_kerja': 23,
    'nearest_road_lokasi_kode': 24,
    'Validasi': 25,
    'distance_m': 32,
    'within_50m': 33, 'within_100m': 34, 'within_150m': 35,
    'within_200m': 36, 'within_60m': 37,
}

# Build column data
columns = {k: [] for k in COL}
columns['geometry'] = []

validasi_map = {
    'Valid': 'Valid', 'valid': 'Valid',
    'Tidak Valid': 'Tidak Valid', 'Tidak valid': 'Tidak Valid', 'tidak valid': 'Tidak Valid',
}

float_cols = {'KODE POS', 'LINTANG', 'BUJUR', 'nearest_road_panjang_km', 'nearest_road_lokasi_kode', 'distance_m'}
bool_cols = {'within_50m', 'within_100m', 'within_150m', 'within_200m', 'within_60m'}

for row in data_rows:
    for col_name, col_idx in COL.items():
        val = row[col_idx] if col_idx < len(row) else None

        if col_name == 'Validasi':
            val_str = str(val).strip() if val else ''
            val = validasi_map.get(val_str, val_str)
        elif col_name in float_cols:
            try:
                val = float(val) if val is not None else None
            except (ValueError, TypeError):
                val = None
        elif col_name in bool_cols:
            val = str(val).strip().lower() == 'true' if val is not None else False

        columns[col_name].append(val)

    # Create geometry from lat/lon
    lat = row[11]
    lon = row[12]
    try:
        wkb = lonlat_to_wkb(float(lon), float(lat))
    except (ValueError, TypeError):
        wkb = None
    columns['geometry'].append(wkb)

n = len(columns['Jenjang'])
print(f"Processed {n} rows")

# Build pyarrow schema and table
schema_fields = []
for col_name in columns:
    if col_name in bool_cols:
        schema_fields.append(pa.field(col_name, pa.bool_()))
    elif col_name in float_cols:
        schema_fields.append(pa.field(col_name, pa.float64()))
    elif col_name == 'geometry':
        schema_fields.append(pa.field(col_name, pa.binary()))
    else:
        schema_fields.append(pa.field(col_name, pa.large_string()))

schema = pa.schema(schema_fields)

def make_array(data, col_name):
    if col_name in bool_cols:
        return pa.array(data, type=pa.bool_())
    elif col_name in float_cols:
        return pa.array(data, type=pa.float64())
    elif col_name == 'geometry':
        return pa.array(data, type=pa.binary())
    else:
        return pa.array(data, type=pa.large_string())

arrays = [make_array(columns[col_name], col_name) for col_name in columns]
table = pa.table(arrays, schema=schema)

out_path = r'C:\Users\pirate-1\Documents\2. Sistem dan Development\3. Repos\PetaSekolahJalanProvinsi\sekolah_377.parquet'
pq.write_table(table, out_path)
print(f"Written to {out_path}")
print(f"Schema: {table.schema}")

# Verify
pf = pq.read_schema(out_path)
print("\n=== VERIFICATION ===")
for field in pf:
    print(f"  {field.name}: {field.type}")
