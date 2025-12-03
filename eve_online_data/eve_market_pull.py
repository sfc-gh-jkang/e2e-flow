"""
EVE Online Market Data Puller using Mokaam.dk API

Pulls historic market data from EVE Online using the Mokaam.dk API.
API Documentation: https://mokaam.dk/

Available Regions:
- 19000001: Global Market (PLEX only)
- 10000002: The Forge
- 10000043: Domain
- 10000016: Lonetrek
- 10000032: Sinq Laison
- 10000060: Delve
- 10000066: Perrigen Falls
- 10000042: Metropolis
- 10000030: Heimatar
- 10000003: Vale of the Silent
- 10000058: Fountain
"""

import requests
import csv
from datetime import datetime
import time
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

# ============================================================================
# CONFIGURATION
# ============================================================================

# A4E Data Regions (Adam4Eve API - 3 regions available)
# These regions have additional data sources from Adam4Eve API
A4E_REGIONS = ["forge", "sinq_laison", "domain"]

REGION_CONFIG = {
    "forge": {
        "region_id": 10000002,
        "name": "The Forge",
        "filename": "eve_market_the_forge",
        "a4e_data": True
    },
    "domain": {
        "region_id": 10000043,
        "name": "Domain",
        "filename": "eve_market_domain",
        "a4e_data": True
    },
    "sinq_laison": {
        "region_id": 10000032,
        "name": "Sinq Laison",
        "filename": "eve_market_sinq_laison",
        "a4e_data": True
    },
    "delve": {
        "region_id": 10000060,
        "name": "Delve",
        "filename": "eve_market_delve",
        "a4e_data": False
    },
    "lonetrek": {
        "region_id": 10000016,
        "name": "Lonetrek",
        "filename": "eve_market_lonetrek",
        "a4e_data": False
    },
    "perrigen_falls": {
        "region_id": 10000066,
        "name": "Perrigen Falls",
        "filename": "eve_market_perrigen_falls",
        "a4e_data": False
    },
    "metropolis": {
        "region_id": 10000042,
        "name": "Metropolis",
        "filename": "eve_market_metropolis",
        "a4e_data": False
    },
    "heimatar": {
        "region_id": 10000030,
        "name": "Heimatar",
        "filename": "eve_market_heimatar",
        "a4e_data": False
    },
    "vale_of_the_silent": {
        "region_id": 10000003,
        "name": "Vale of the Silent",
        "filename": "eve_market_vale_of_the_silent",
        "a4e_data": False
    },
    "fountain": {
        "region_id": 10000058,
        "name": "Fountain",
        "filename": "eve_market_fountain",
        "a4e_data": False
    }
}

# SELECT REGION (only used if MODE = "specific" or "all")
SELECTED_REGION = "forge"  # Options: "forge", "domain", "sinq_laison", "delve", etc.

# SELECT MODE: "specific", "all", or "all_a4e_regions"
# "specific": Pull specific item types (faster, recommended)
# "all": Pull all items for the selected region (slow, large dataset)
# "all_a4e_regions": Pull all items from the 3 A4E regions only (The Forge, Sinq Laison, Domain) - DEFAULT
MODE = "all_a4e_regions"

# RATE LIMITING CONFIGURATION
# To avoid getting blocked by the API (returns 403 Forbidden if you hit too hard)
# Recommended: Keep delays at 5+ seconds for "all" endpoints
RATE_LIMIT_CONFIG = {
    "delay_between_regions": 5,  # Seconds between each region in all_regions mode
    "delay_after_large_request": 2,  # Seconds after pulling all items from a region
    "retry_on_403": True,  # Retry if rate limited (403 Forbidden)
    "max_retries": 3,  # Maximum retry attempts
    "retry_delay": 10  # Seconds to wait before retrying after 403
}

# SPECIFIC ITEM TYPE IDS (if MODE = "specific")
# Example popular items:
# 44992 = PLEX
# 34 = Tritanium
# 35 = Pyerite
# 36 = Mexallon
# 37 = Isogen
# 38 = Nocxium
# 39 = Zydrine
# 40 = Megacyte
TYPE_IDS = [44992, 34, 35, 36, 37, 38, 39, 40]  # Add your item type IDs here

CONFIG = {
    "region": SELECTED_REGION,
    "mode": MODE,
    "type_ids": TYPE_IDS,
    "filename": REGION_CONFIG[SELECTED_REGION]["filename"] if MODE != "all_a4e_regions" else "eve_market_all_a4e_regions",
    "include_date_in_file_name": True,
    "logging": "on"  # Options: "off", "on"
}

BASE_URL = "https://mokaam.dk/API/market"


def print_log(message):
    """Simple logger"""
    if CONFIG["logging"] == "on":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")


def check_api_update_window():
    """
    Check if we're in the API update window (12:05 PM UTC ± 10 minutes)
    Returns warning message if in update window, None otherwise
    """
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    current_hour = now_utc.hour
    current_minute = now_utc.minute
    
    # Update window: 11:55 - 12:15 UTC
    if current_hour == 11 and current_minute >= 55:
        return "⚠️  WARNING: API update window (12:05 PM UTC). You may experience errors."
    elif current_hour == 12 and current_minute <= 15:
        return "⚠️  WARNING: API update window (12:05 PM UTC). You may experience errors."
    return None


def make_api_request(url, timeout=60):
    """
    Make an API request with exponential backoff retry logic for 403 rate limiting
    Returns (success: bool, data: dict or None, status_code: int)
    
    Exponential backoff: Each retry waits progressively longer
    - Retry 1: 10 seconds
    - Retry 2: 20 seconds  
    - Retry 3: 40 seconds
    """
    max_retries = RATE_LIMIT_CONFIG["max_retries"] if RATE_LIMIT_CONFIG["retry_on_403"] else 1
    base_retry_delay = RATE_LIMIT_CONFIG["retry_delay"]
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            
            if response.status_code == 200:
                return True, response.json(), 200
            elif response.status_code == 403:
                if attempt < max_retries - 1:
                    # Exponential backoff: delay = base_delay * (2 ^ attempt)
                    wait_time = base_retry_delay * (2 ** attempt)
                    print_log(f"⚠️  Rate limited (403 Forbidden). Exponential backoff: waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    print_log("❌ 403 Forbidden - Rate limited after max retries")
                    print_log("   Contact Mokaam on Oz's discord or in-game: Mokaam Racor")
                    return False, None, 403
            else:
                print_log(f"❌ API Error: Status {response.status_code}")
                print_log(f"   Response: {response.text[:200]}")
                return False, None, response.status_code
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                # Use half the exponential backoff for timeouts
                wait_time = (base_retry_delay / 2) * (2 ** attempt)
                print_log(f"⚠️  Request timeout. Exponential backoff: waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                time.sleep(wait_time)
                continue
            else:
                print_log("❌ Request timeout after max retries")
                return False, None, 0
        except Exception as e:
            print_log(f"❌ Exception: {e}")
            return False, None, 0
    
    return False, None, 0


def get_type_ids():
    """
    Get all available type IDs from the API
    Returns dict mapping type_id to item name
    """
    print_log("📋 Fetching available type IDs...")
    
    url = f"{BASE_URL}/type_ids"
    success, data, status_code = make_api_request(url, timeout=30)
    
    if success and data:
        print_log(f"✅ Retrieved {len(data)} item types")
        return data
    else:
        print_log(f"❌ Failed to fetch type IDs (status: {status_code})")
        return {}


def get_market_data_specific(region_id, type_ids, region_key=None):
    """
    Get market data for specific item types
    Following API best practices: comma-separated type IDs in one request
    """
    if region_key is None:
        region_key = CONFIG["region"]
    region_name = REGION_CONFIG[region_key]["name"]
    print_log(f"🔍 Querying market data for {len(type_ids)} items in {region_name}...")
    
    # Convert type IDs to comma-separated string
    type_id_str = ",".join(map(str, type_ids))
    
    url = f"{BASE_URL}/items?regionid={region_id}&typeid={type_id_str}"
    print_log(f"   URL: {url}")
    
    success, data, status_code = make_api_request(url, timeout=30)
    
    if success and data:
        # Convert dict to list of items and add region info
        items = []
        for type_id, item_data in data.items():
            if isinstance(item_data, dict):
                item_data['typeid'] = type_id
                item_data['region_id'] = region_id
                item_data['region_name'] = region_name
                items.append(item_data)
        
        print_log(f"✅ Retrieved data for {len(items)} items")
        return items
    else:
        print_log(f"❌ Failed to retrieve data (status: {status_code})")
        return []


def get_market_data_all(region_id, region_key=None):
    """
    Get market data for ALL items in a region
    WARNING: This returns a lot of data!
    """
    if region_key is None:
        region_key = CONFIG["region"]
    region_name = REGION_CONFIG[region_key]["name"]
    print_log(f"🔍 Querying ALL market data for {region_name}...")
    print_log("   ⚠️  This may take a while and return a large dataset")
    
    url = f"{BASE_URL}/all?regionid={region_id}"
    print_log(f"   URL: {url}")
    
    success, data, status_code = make_api_request(url, timeout=60)
    
    if success and data:
        # Convert dict to list of items and add region info
        items = []
        for type_id, item_data in data.items():
            if isinstance(item_data, dict):
                item_data['typeid'] = type_id
                item_data['region_id'] = region_id
                item_data['region_name'] = region_name
                items.append(item_data)
        
        print_log(f"✅ Retrieved data for {len(items)} items")
        
        # Add delay after large request to avoid rate limiting
        delay = RATE_LIMIT_CONFIG["delay_after_large_request"]
        if delay > 0:
            print_log(f"   ⏳ Rate limiting: Waiting {delay} seconds after large request...")
            time.sleep(delay)
        
        return items
    else:
        print_log(f"❌ Failed to retrieve data (status: {status_code})")
        return []


def get_market_data_all_regions():
    """
    Get market data for ALL items from ALL A4E regions
    (The Forge, Sinq Laison, Domain)
    WARNING: This returns a HUGE dataset!
    """
    print_log("🔍 Querying ALL market data for ALL A4E regions...")
    print_log(f"   Regions: {', '.join([REGION_CONFIG[r]['name'] for r in A4E_REGIONS])}")
    print_log("   ⚠️  This will take several minutes and return a very large dataset")
    
    all_items = []
    
    for region_key in A4E_REGIONS:
        region_config = REGION_CONFIG[region_key]
        region_id = region_config["region_id"]
        region_name = region_config["name"]
        
        print()
        print_log(f"📊 Pulling data for {region_name} (ID: {region_id})...")
        
        items = get_market_data_all(region_id, region_key)
        
        if items:
            all_items.extend(items)
            print_log(f"   ✅ Added {len(items)} items from {region_name}")
        else:
            print_log(f"   ⚠️  No items retrieved from {region_name}")
        
        # Add delay between regions to avoid rate limiting
        if region_key != A4E_REGIONS[-1]:  # Don't delay after last region
            delay = RATE_LIMIT_CONFIG["delay_between_regions"]
            print_log(f"   ⏳ Rate limiting: Waiting {delay} seconds before next region...")
            time.sleep(delay)
    
    print()
    print_log(f"✅ Total items retrieved from all regions: {len(all_items)}")
    return all_items


def save_to_csv(items, filename, type_id_names=None):
    """Save market data to CSV file"""
    if not items:
        print_log("❌ No data to save")
        return None
    
    # Add date to filename if configured
    if CONFIG["include_date_in_file_name"]:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{date_str}.csv"
    else:
        filename = f"{filename}.csv"
    
    # Save in eve_online_data folder
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, filename)
    
    # Define CSV columns (main fields from Mokaam API)
    fieldnames = [
        "region_id",
        "region_name",
        "typeid",
        "item_name",
        "timestamp_pulled",
        "last_data",
        "vol_yesterday",
        "vol_week",
        "vol_month",
        "avg_price_yesterday",
        "avg_price_week",
        "avg_price_month",
        "size_yesterday",
        "size_week",
        "size_month",
        "high_yesterday",
        "high_week",
        "high_month",
        "low_yesterday",
        "low_week",
        "low_month",
        "vwap_week",
        "vwap_month",
        "_52w_high",
        "_52w_low"
    ]
    
    # Get current UTC timestamp for Snowflake compatibility
    # Format: YYYY-MM-DD HH:MM:SS (TIMESTAMP_NTZ format)
    from datetime import timezone
    utc_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for item in items:
                # Add item name if available
                if type_id_names and str(item['typeid']) in type_id_names:
                    name_data = type_id_names[str(item['typeid'])]
                    # Extract just the name string if it's a dict
                    if isinstance(name_data, dict):
                        item['item_name'] = name_data.get('name', 'Unknown')
                    else:
                        item['item_name'] = name_data
                else:
                    item['item_name'] = "Unknown"
                
                # Add timestamp_pulled in Snowflake-compatible format
                item['timestamp_pulled'] = utc_timestamp
                
                writer.writerow(item)
        
        print_log(f"✅ Saved {len(items)} items to {filename}")
        return filename
        
    except Exception as e:
        print_log(f"❌ Error saving CSV: {e}")
        return None


def pull_eve_market_data() -> str:
    """Pull EVE market data from the Mokaam.dk API and save to CSV.
    
    Returns:
        str: The filename of the CSV file

    Example:
        >>> from eve_online_data.eve_market_pull import pull_eve_market_data
        >>> csv_file = pull_eve_market_data()
        >>> print(csv_file)
        eve_market_all_a4e_regions_20251203_135659.csv
    """
    
    print("\n" + "=" * 100)
    if CONFIG['mode'] == 'all_a4e_regions':
        print("🎮 EVE Online Market Data Puller - ALL A4E REGIONS (3 Regions)")
        print("=" * 100)
        print(f"API: https://mokaam.dk/")
        print()
        print_log(f"📊 Mode: {CONFIG['mode']}")
        print_log(f"📊 A4E Regions: {', '.join([REGION_CONFIG[r]['name'] for r in A4E_REGIONS])}")
        print_log(f"   Note: Pulling from 3 A4E regions only (not all 10 available regions)")
        region_name = "All A4E Regions"
        region_id = None
    else:
        region_config = REGION_CONFIG[CONFIG["region"]]
        region_name = region_config["name"]
        region_id = region_config["region_id"]
        
        print(f"🎮 EVE Online Market Data Puller - {region_name}")
        print("=" * 100)
        print(f"API: https://mokaam.dk/")
        print()
        
        print_log(f"📊 Region: {region_name} (ID: {region_id})")
        print_log(f"📊 Mode: {CONFIG['mode']}")
        
        if CONFIG['mode'] == 'specific':
            print_log(f"📊 Items to pull: {len(CONFIG['type_ids'])}")
            print_log(f"   Type IDs: {CONFIG['type_ids']}")
    
    print()
    
    # Check for API update window
    update_warning = check_api_update_window()
    if update_warning:
        print_log(update_warning)
        print_log("   If you experience errors, wait 10-15 minutes and try again.")
        print()
    
    # Display rate limiting configuration
    print_log("⚙️  Rate Limiting Configuration:")
    print_log(f"   Retry on 403: {RATE_LIMIT_CONFIG['retry_on_403']} (max {RATE_LIMIT_CONFIG['max_retries']} retries)")
    print_log(f"   Delay between regions: {RATE_LIMIT_CONFIG['delay_between_regions']}s")
    print_log(f"   Delay after large request: {RATE_LIMIT_CONFIG['delay_after_large_request']}s")
    print()
    
    # Optional: Get type ID names for better CSV output
    type_id_names = None
    if CONFIG['mode'] == 'specific' and len(CONFIG['type_ids']) <= 20:
        type_id_names = get_type_ids()
        print()
    
    # Step 1: Get market data
    print_log("📊 STEP 1: Fetching Market Data")
    print_log("-" * 100)
    
    if CONFIG['mode'] == 'all_a4e_regions':
        items = get_market_data_all_regions()
    elif CONFIG['mode'] == 'specific':
        items = get_market_data_specific(region_id, CONFIG['type_ids'])
    else:  # mode == 'all'
        items = get_market_data_all(region_id)
    
    if not items:
        print_log("❌ No data retrieved. Exiting.")
        return
    
    print()
    
    # Step 2: Display summary
    print_log("📊 STEP 2: Summary Statistics")
    print_log("-" * 100)
    print_log(f"Total items: {len(items)}")
    
    # Count valid data points
    valid_items = [i for i in items if i.get('last_data') not in ['Null', 'Itemid not found', None]]
    print_log(f"Items with valid data: {len(valid_items)}")
    
    # Show region breakdown if pulling from multiple regions
    if CONFIG['mode'] == 'all_a4e_regions':
        region_counts = {}
        for item in items:
            region = item.get('region_name', 'Unknown')
            region_counts[region] = region_counts.get(region, 0) + 1
        
        print_log("Items by region:")
        for region, count in sorted(region_counts.items()):
            print_log(f"  - {region}: {count:,} items")
    
    if valid_items:
        # Show top 5 by volume
        sorted_by_vol = sorted(
            valid_items, 
            key=lambda x: float(x.get('vol_month', 0) or 0), 
            reverse=True
        )[:5]
        
        print_log("Top 5 by monthly volume:")
        for item in sorted_by_vol:
            type_id = item.get('typeid', 'N/A')
            vol = item.get('vol_month', 'N/A')
            price = item.get('avg_price_month', 'N/A')
            region = item.get('region_name', 'N/A')
            if type_id_names and str(type_id) in type_id_names:
                name_data = type_id_names[str(type_id)]
                name = name_data.get('name', 'Unknown') if isinstance(name_data, dict) else name_data
            else:
                name = type_id
            print_log(f"  - {name} (ID: {type_id}, Region: {region}): Volume={vol}, Avg Price={price}")
    
    print()
    
    # Step 3: Save to CSV
    print_log("📊 STEP 3: Saving to CSV")
    print_log("-" * 100)
    
    csv_file = save_to_csv(items, CONFIG["filename"], type_id_names)
    
    if csv_file:
        print()
        print_log("✅ Data pull complete!")
        print_log(f"📄 Output file: {csv_file}")
    
    print()
    print("=" * 100)
    print()

    return csv_file


# Pandera schema for EVE market data validation
EveMarketSchema = DataFrameSchema(
    {
        # Identifiers
        "region_id": Column(int, Check.gt(0), coerce=True, description="EVE region ID"),
        "typeid": Column(int, Check.gt(0), coerce=True, description="Item type ID"),
        
        # String columns
        "region_name": Column(str, coerce=True, description="Region name"),
        "item_name": Column(str, coerce=True, description="Item name"),
        
        # Datetime columns
        "timestamp_pulled": Column(pa.DateTime, coerce=True, description="When data was pulled"),
        "last_data": Column(str, coerce=True, description="Last data date"),  # Keep as string, convert later
        
        # Volume metrics (nullable floats, must be >= 0)
        "vol_yesterday": Column(float, Check.ge(0), nullable=True, coerce=True, description="Volume yesterday"),
        "vol_week": Column(float, Check.ge(0), nullable=True, coerce=True, description="Volume this week"),
        "vol_month": Column(float, Check.ge(0), nullable=True, coerce=True, description="Volume this month"),
        
        # Price metrics (nullable floats, must be >= 0)
        "avg_price_yesterday": Column(float, Check.ge(0), nullable=True, coerce=True, description="Avg price yesterday"),
        "avg_price_week": Column(float, Check.ge(0), nullable=True, coerce=True, description="Avg price this week"),
        "avg_price_month": Column(float, Check.ge(0), nullable=True, coerce=True, description="Avg price this month"),
        
        # Size/value metrics (nullable floats, must be >= 0)
        "size_yesterday": Column(float, Check.ge(0), nullable=True, coerce=True, description="ISK value yesterday"),
        "size_week": Column(float, Check.ge(0), nullable=True, coerce=True, description="ISK value this week"),
        "size_month": Column(float, Check.ge(0), nullable=True, coerce=True, description="ISK value this month"),
        
        # High prices (nullable floats, must be >= 0)
        "high_yesterday": Column(float, Check.ge(0), nullable=True, coerce=True, description="High price yesterday"),
        "high_week": Column(float, Check.ge(0), nullable=True, coerce=True, description="High price this week"),
        "high_month": Column(float, Check.ge(0), nullable=True, coerce=True, description="High price this month"),
        
        # Low prices (nullable floats, must be >= 0)
        "low_yesterday": Column(float, Check.ge(0), nullable=True, coerce=True, description="Low price yesterday"),
        "low_week": Column(float, Check.ge(0), nullable=True, coerce=True, description="Low price this week"),
        "low_month": Column(float, Check.ge(0), nullable=True, coerce=True, description="Low price this month"),
        
        # VWAP (Volume Weighted Average Price)
        "vwap_week": Column(float, Check.ge(0), nullable=True, coerce=True, description="VWAP this week"),
        "vwap_month": Column(float, Check.ge(0), nullable=True, coerce=True, description="VWAP this month"),
        
        # 52-week high/low
        "_52w_high": Column(float, Check.ge(0), nullable=True, coerce=True, description="52-week high"),
        "_52w_low": Column(float, Check.ge(0), nullable=True, coerce=True, description="52-week low"),
    },
    coerce=True,
    strict=False,  # Allow extra columns
)


def validate_eve_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and coerce EVE market DataFrame using pandera schema.
    
    Args:
        df: Raw DataFrame from CSV
        
    Returns:
        pd.DataFrame: Validated DataFrame with correct data types
        
    Raises:
        pandera.errors.SchemaError: If validation fails
    """
    validated_df = EveMarketSchema.validate(df)
    
    # Convert last_data to date object after validation
    # Use errors='coerce' to handle invalid values like "ERROR: 404" -> NaT
    if 'last_data' in validated_df.columns:
        validated_df['last_data'] = pd.to_datetime(
            validated_df['last_data'], 
            errors='coerce'
        ).dt.date
        
        # Filter out rows with NULL last_data (invalid data that can't be used as PK)
        null_count = validated_df['last_data'].isna().sum()
        if null_count > 0:
            print(f"⚠ Filtering out {null_count} rows with invalid last_data (NULL)")
            validated_df = validated_df[validated_df['last_data'].notna()]
    
    return validated_df


def read_eve_market_data_from_csv(csv_file: str, validate: bool = True) -> pd.DataFrame:
    """Read the eve market data from the CSV file and return as a pandas DataFrame.
    
    Args:
        csv_file: Path to the CSV file
        validate: If True, validate data using pandera schema (default: True)
        
    Returns:
        pd.DataFrame: DataFrame containing the eve market data with correct dtypes
        
    Raises:
        pandera.errors.SchemaError: If validation is enabled and data fails validation
    """
    df = pd.read_csv(csv_file)
    
    if validate:
        df = validate_eve_market_data(df)
    
    return df



if __name__ == "__main__":
    # csv_file_path_name = pull_eve_market_data()
    csv_file_path_name = Path("eve_online_data", "eve_market_all_a4e_regions_20251203_135659.csv")
    eve_market_data_df = read_eve_market_data_from_csv(csv_file_path_name)
    print("✓ Data validated successfully with pandera!")
    print(f"\nShape: {eve_market_data_df.shape}")
    print(f"\nData types:\n{eve_market_data_df.dtypes}")
    print(f"\nFirst 3 rows:\n{eve_market_data_df.head(3)}")
