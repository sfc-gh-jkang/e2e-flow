# EVE Online Market Data Puller

Pull historic market data from EVE Online using the **Mokaam.dk API**.

## 📚 API Documentation

- **Main Site:** [https://mokaam.dk/](https://mokaam.dk/)
- **Data Source:** EVE Online ESI Market History
- **Update Schedule:** Daily at 12:05 PM UTC

## 🚀 Quick Start

### 1. Run the Script (Default: All A4E Regions)

```bash
cd /Users/jkang/Documents/vscode/e2e-flow
uv run eve_online_data/eve_market_pull.py
```

**By default**, the script pulls **ALL items from the 3 A4E regions** (The Forge, Sinq Laison, Domain):

- ~57,000 items total
- ~45,000 items with valid data
- Takes ~30 seconds
- Includes `region_id` and `region_name` columns
- **Note:** Only pulls from 3 A4E regions, not all 10 available regions

### 2. Configure What to Pull

Edit `eve_market_pull.py` and configure:

#### **Select Mode**

```python
MODE = "all_a4e_regions"  # Options: "specific", "all", or "all_a4e_regions"
```

- `"all_a4e_regions"` - Pull ALL items from the 3 A4E regions only **(DEFAULT)**
- `"specific"` - Pull specific items from one region (fastest)
- `"all"` - Pull ALL items from one region (slow, large dataset)

#### **Select Region** (only for "specific" or "all" modes)

```python
SELECTED_REGION = "forge"  # Options: "forge", "domain", "sinq_laison", "delve", etc.
```

**A4E Data Regions (Adam4Eve API - 3 regions with extended data):**

- `"forge"` - The Forge (Jita - highest volume) ✅
- `"sinq_laison"` - Sinq Laison (Dodixie) ✅
- `"domain"` - Domain (Amarr) ✅

**ESI Data Regions (7 additional regions):**

- `"delve"` - Delve (Null-sec)
- `"lonetrek"` - Lonetrek
- `"perrigen_falls"` - Perrigen Falls
- `"metropolis"` - Metropolis
- `"heimatar"` - Heimatar
- `"vale_of_the_silent"` - Vale of the Silent
- `"fountain"` - Fountain

#### **Select Items (if MODE = "specific")**

```python
TYPE_IDS = [44992, 34, 35, 36, 37, 38, 39, 40]
```

Popular Item Type IDs:

- `44992` - PLEX
- `34` - Tritanium
- `35` - Pyerite
- `36` - Mexallon
- `37` - Isogen
- `38` - Nocxium
- `39` - Zydrine
- `40` - Megacyte

## 📊 Data Fields Returned

The API returns extensive market statistics:

| Field | Description |
|-------|-------------|
| `region_id` | Region ID (e.g., 10000002 for The Forge) |
| `region_name` | Region name (e.g., "The Forge", "Sinq Laison", "Domain") |
| `typeid` | Item type ID |
| `item_name` | Item name (if available) |
| `timestamp_pulled` | UTC timestamp when data was pulled (Snowflake-compatible: YYYY-MM-DD HH:MM:SS) |
| `last_data` | Last data update timestamp from API |
| `vol_yesterday` | Volume traded yesterday |
| `vol_week` | Median volume last week |
| `vol_month` | Median volume last month |
| `avg_price_yesterday` | Average price yesterday |
| `avg_price_week` | Median avg price last week |
| `avg_price_month` | Median avg price last month |
| `size_yesterday` | Market size yesterday (price × volume) |
| `size_week` | Median market size last week |
| `size_month` | Median market size last month |
| `high_yesterday` | Highest price yesterday |
| `high_week` | Median highest price last week |
| `high_month` | Median highest price last month |
| `low_yesterday` | Lowest price yesterday |
| `low_week` | Median lowest price last week |
| `low_month` | Median lowest price last month |
| `vwap_week` | Volume-weighted avg price last week |
| `vwap_month` | Volume-weighted avg price last month |
| `_52w_high` | 52-week high |
| `_52w_low` | 52-week low |

**Full fields available:** quarter, year, order counts, spreads, standard deviations, and more!

## 📋 Available Regions

### ESI Data Regions (10 available)

| Region | Region ID | Description |
|--------|-----------|-------------|
| Global Market | 19000001 | PLEX only |
| The Forge | 10000002 | Jita (highest volume) |
| Domain | 10000043 | Amarr |
| Lonetrek | 10000016 | Caldari space |
| Sinq Laison | 10000032 | Dodixie |
| Delve | 10000060 | Null-sec (Goons) |
| Perrigen Falls | 10000066 | Null-sec |
| Metropolis | 10000042 | Minmatar space |
| Heimatar | 10000030 | Minmatar space |
| Vale of the Silent | 10000003 | Null-sec |
| Fountain | 10000058 | Null-sec |

## 💡 Example Use Cases

### 1. Track PLEX Prices

```python
MODE = "specific"
TYPE_IDS = [44992]  # PLEX only
SELECTED_REGION = "forge"  # Jita
```

### 2. Monitor Mineral Prices

```python
MODE = "specific"
TYPE_IDS = [34, 35, 36, 37, 38, 39, 40]  # All minerals
SELECTED_REGION = "forge"
```

### 3. Pull All Market Data for Analysis

```python
MODE = "all"
SELECTED_REGION = "forge"
# WARNING: This returns thousands of items!
```

## ⚠️ Important API Guidelines

From the Mokaam.dk documentation:

1. **Use comma-separated type IDs** - Don't make a request for each item individually
2. **Rate Limiting** - If you get 403 status, you've been rate limited
3. **Contact for Issues** - IGN: Mokaam Racor or Mokaam on Discord

The script follows best practices by combining type IDs into a single request.

## 🔍 Finding Item Type IDs

### Option 1: Use EVE Online Tools

- **Fuzzwork Type ID Lookup:** [https://www.fuzzwork.co.uk/](https://www.fuzzwork.co.uk/)
- **EVE Market Data:** [https://evemarketer.com/](https://evemarketer.com/)

### Option 2: Query the API

The script can fetch all available type IDs:

```python
# In the script, this is done automatically when pulling specific items
type_id_names = get_type_ids()
```

## 📁 Output Format

CSV file with columns:

```csv
region_id,region_name,typeid,item_name,timestamp_pulled,last_data,vol_yesterday,vol_week,vol_month,avg_price_yesterday,...
10000002,The Forge,44992,PLEX,2025-10-31 21:24:07,2025-10-30,0.0,0.0,0.0,5975000.0,...
10000002,The Forge,34,Tritanium,2025-10-31 21:24:07,2025-10-30,3714217954.0,3714217954.0,4405645035.5,4.29,...
10000032,Sinq Laison,34,Tritanium,2025-10-31 21:24:07,2025-10-30,248172543.0,248172543.0,301543221.5,4.15,...
10000043,Domain,34,Tritanium,2025-10-31 21:24:07,2025-10-30,621177376.5,621177376.5,621177376.5,3.38,...
```

Filename format:

```text
eve_market_the_forge_20251031_164500.csv
```

### Snowflake Upload Compatibility

The CSV includes a `timestamp_pulled` column in UTC format (`YYYY-MM-DD HH:MM:SS`) that is directly compatible with Snowflake's `TIMESTAMP_NTZ` data type.

Example Snowflake table schema:

```sql
CREATE TABLE eve_market_data (
    region_id INTEGER,
    region_name VARCHAR(50),
    typeid INTEGER,
    item_name VARCHAR(255),
    timestamp_pulled TIMESTAMP_NTZ,
    last_data VARCHAR(50),
    vol_yesterday FLOAT,
    vol_week FLOAT,
    vol_month FLOAT,
    avg_price_yesterday FLOAT,
    avg_price_week FLOAT,
    avg_price_month FLOAT,
    size_yesterday FLOAT,
    size_week FLOAT,
    size_month FLOAT,
    high_yesterday FLOAT,
    high_week FLOAT,
    high_month FLOAT,
    low_yesterday FLOAT,
    low_week FLOAT,
    low_month FLOAT,
    vwap_week FLOAT,
    vwap_month FLOAT,
    _52w_high FLOAT,
    _52w_low FLOAT
);

-- Load data from all regions
COPY INTO eve_market_data
FROM @your_stage/eve_market_all_a4e_regions_20251031_172407.csv
FILE_FORMAT = (TYPE = CSV SKIP_HEADER = 1);

-- Query by region
SELECT * FROM eve_market_data WHERE region_name = 'The Forge' AND typeid = 44992;
```

## ⚙️ Rate Limiting & API Protection

**The script includes built-in rate limiting to prevent you from getting blocked!**

### Automatic Rate Limiting Features

```python
RATE_LIMIT_CONFIG = {
    "delay_between_regions": 5,  # Seconds between each region
    "delay_after_large_request": 2,  # Seconds after pulling all items
    "retry_on_403": True,  # Automatically retry if rate limited
    "max_retries": 3,  # Maximum retry attempts
    "retry_delay": 10  # Seconds to wait before retrying
}
```

### What the Script Does Automatically

1. ✅ **Delays Between Regions**: 5-second wait between pulling from each region
2. ✅ **Delays After Large Requests**: 2-second wait after pulling all items from a region
3. ✅ **Exponential Backoff Retry**: If rate limited (403), retries with progressively longer waits:
   - Retry 1: 10 seconds
   - Retry 2: 20 seconds
   - Retry 3: 40 seconds
4. ✅ **API Update Window Detection**: Warns you if pulling during the API update window (12:05 PM UTC ± 10 min)
5. ✅ **Timeout Handling**: Automatically retries with exponential backoff if requests timeout

### Rate Limiting in Action

```text
[2025-10-31 17:30:50] ⚙️  Rate Limiting Configuration:
[2025-10-31 17:30:50]    Retry on 403: True (max 3 retries)
[2025-10-31 17:30:50]    Delay between regions: 5s
[2025-10-31 17:30:50]    Delay after large request: 2s

[2025-10-31 17:30:58]    ⏳ Rate limiting: Waiting 5 seconds before next region...
```

### Customizing Rate Limits

You can adjust these in `eve_market_pull.py` if needed:

```python
RATE_LIMIT_CONFIG = {
    "delay_between_regions": 10,  # Increase to 10 seconds for extra safety
    "delay_after_large_request": 5,  # Increase delay after large requests
    "retry_on_403": True,  # Keep retry enabled
    "max_retries": 5,  # Allow more retry attempts
    "retry_delay": 15  # Wait longer before retrying
}
```

## 🛠️ Troubleshooting

### 403 Forbidden Error

If you still get rate limited despite built-in protections:

- ✅ **Automatic retry** will handle this (waits 10 seconds and retries up to 3 times)
- If retries fail: Wait 10-15 minutes before running the script again
- Increase delay settings in `RATE_LIMIT_CONFIG`
- Contact Mokaam (IGN: Mokaam Racor) if issue persists

### No Data Returned

- Check if the region ID is correct
- Verify type IDs exist in EVE Online
- Check API status at [https://mokaam.dk/](https://mokaam.dk/)

### Update Time Issues

Data updates daily at 12:05 PM UTC. During updates (10-15 min window), you may get errors. Wait and try again.

## 📧 Support

- **API Creator:** Mokaam Racor (EVE Online)
- **Discord:** Mokaam on Oz's Discord
- **API Website:** [https://mokaam.dk/](https://mokaam.dk/)

## 🙏 Credits

This API is maintained by Mokaam and runs on his personal server.

Thanks to:

- Steve from Fuzzwork
- Ethan from Adam4eve
- Shikkoken and Bonsailinse from Oz community
- Phaelim O'Neil (Lanarion) for Excel guide

---

**Made with ❤️ for EVE Online market traders**
