# Database Scripts

This directory contains utility scripts for managing database data.

## City Data Management

### Files

- `excel_to_csv.py` - Converts `backup/amap_adcode_citycode.xlsx` to CSV format
- `import_cities.py` - Imports cities from CSV into the database

### Quick Start

**Import cities from Excel backup:**
```bash
make db-seed-cities
```

This command will:
1. Convert `backup/amap_adcode_citycode.xlsx` to `backend/data/china-city-20250620.csv`
2. Import all 3,240 cities into the `cities` table

### Individual Commands

**Convert Excel to CSV:**
```bash
make db-convert-cities
```

**Import from CSV:**
```bash
make db-import-cities
```

**Check cities count:**
```bash
make db-cities-count
```

### Manual Usage

**Convert Excel to CSV:**
```bash
cd backend
poetry run python scripts/excel_to_csv.py
```

**Import cities:**
```bash
cd backend
poetry run python scripts/import_cities.py
```

**Import with custom CSV:**
```bash
cd backend
poetry run python scripts/import_cities.py --csv path/to/custom.csv --batch-size 200
```

### CSV Format

The CSV file should have the following columns:

| Column | Required | Description |
|--------|----------|-------------|
| `Location_ID` | Yes | Unique location identifier (ad_code) |
| `Location_Name_ZH` | Yes | Chinese name |
| `Location_Name_EN` | No | English name |
| `AD_code` | Yes | 6-digit administrative division code |
| `Adm1_Name_ZH` | No | Province name (Chinese) |
| `Adm1_Name_EN` | No | Province name (English) |
| `Adm2_Name_ZH` | No | City name (Chinese) |
| `Adm2_Name_EN` | No | City name (English) |
| `Latitude` | No | Latitude coordinate |
| `Longitude` | No | Longitude coordinate |
| `Timezone` | No | Timezone identifier |

### Database Schema

```sql
CREATE TABLE cities (
    id INTEGER PRIMARY KEY,
    location_id VARCHAR(20) UNIQUE NOT NULL,
    location_name_zh VARCHAR(100) NOT NULL,
    location_name_en VARCHAR(100),
    ad_code VARCHAR(10) UNIQUE NOT NULL,
    province_zh VARCHAR(50),
    province_en VARCHAR(50),
    city_zh VARCHAR(50),
    city_en VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT,
    timezone VARCHAR(50)
);
```

### Troubleshooting

**Duplicate entries:**
- The script automatically skips duplicate entries based on `location_id` and `ad_code`
- Check the import output for skipped rows

**Missing openpyxl:**
```bash
cd backend
poetry add openpyxl
```

**Empty table:**
- Verify the Excel file exists at `backup/amap_adcode_citycode.xlsx`
- Check the CSV was generated at `backend/data/china-city-20250620.csv`
- Ensure database migrations are up to date: `make db-upgrade`

### Data Source

The city data comes from Amap (高德地图) administrative division codes:
- **Source**: `backup/amap_adcode_citycode.xlsx`
- **Format**: Excel with columns: 中文名, adcode, citycode
- **Total**: 3,240 cities/districts across China

### Re-importing Data

To re-import from updated Excel:

```bash
# Clear existing data (optional)
cd backend
sqlite3 app.db "DELETE FROM cities;"

# Import fresh data
cd ..
make db-seed-cities
```
