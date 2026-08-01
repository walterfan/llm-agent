#!/usr/bin/env python3
"""
Convert Excel backup to CSV format for import_cities.py
Usage: poetry run python scripts/excel_to_csv.py
"""

import pandas as pd
from pathlib import Path


def convert_excel_to_csv():
    """Convert Excel backup to CSV format expected by import_cities.py"""

    # Paths
    excel_file = Path(__file__).parent.parent.parent / "backup" / "amap_adcode_citycode.xlsx"
    csv_file = Path(__file__).parent.parent / "data" / "china-city-20250620.csv"

    if not excel_file.exists():
        print(f"❌ Excel file not found: {excel_file}")
        return False

    # Create data directory if not exists
    csv_file.parent.mkdir(parents=True, exist_ok=True)

    # Read Excel
    print(f"📖 Reading {excel_file}...")
    df = pd.read_excel(excel_file)
    print(f"✅ Read {len(df)} rows")
    print(f"   Columns: {df.columns.tolist()}")

    # Convert to expected CSV format
    print("🔄 Converting to CSV format...")

    # Map columns - use AD_code as Location_ID for uniqueness
    csv_data = pd.DataFrame({
        'Location_ID': df['adcode'].astype(str).str.zfill(6),  # Use ad_code as unique identifier
        'Location_Name_ZH': df['中文名'],
        'Location_Name_EN': None,  # Not in Excel
        'AD_code': df['adcode'].astype(str).str.zfill(6),  # Ensure 6 digits
        'Adm1_Name_ZH': None,  # Province - not in Excel
        'Adm1_Name_EN': None,
        'Adm2_Name_ZH': None,  # City - not in Excel
        'Adm2_Name_EN': None,
        'Latitude': None,  # Not in Excel
        'Longitude': None,
        'Timezone': None
    })

    # Save to CSV
    print(f"💾 Saving to {csv_file}...")
    csv_data.to_csv(csv_file, index=False, encoding='utf-8')

    print(f"✅ Converted {len(csv_data)} rows to CSV")
    print(f"📁 Output: {csv_file}")

    # Show sample
    print("\n📋 Sample data (first 3 rows):")
    print(csv_data.head(3).to_string())

    return True


if __name__ == "__main__":
    success = convert_excel_to_csv()
    if not success:
        exit(1)
