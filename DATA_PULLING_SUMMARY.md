# Data Pulling Summary - Gaming Market Data

This project now includes two gaming market data pullers:

## 🎮 1. GRID Esports Data (`grid_data/`)

**API:** [GRID API](https://portal.grid.gg/)  
**Games:** Dota 2, CS:GO, CS2  
**Data:** Tournament/series metadata only

### What You CAN Pull ✅

- Series IDs
- Tournament names and IDs
- Game titles
- Series types (ESPORTS, LOOPFEED)
- Scheduled start times

### What You CANNOT Pull ❌

- Team names (requires premium API tier)
- Match winners (requires premium API tier)
- Scores (requires premium API tier)
- Player information (requires premium API tier)

### Usage

```bash
# Pull Dota 2 series metadata
cd /Users/jkang/Documents/vscode/e2e-flow
uv run grid_data/grid_data_pull.py

# Find latest series IDs
uv run grid_data/find_dota2_series.py
uv run grid_data/find_cs2_series.py
```

### Output Example

```csv
series_id,game_title,tournament,tournament_id,series_type,start_time,team_1_name,team_1_id,team_2_name,team_2_id
2863921,Defense of the Ancients 2,BLAST SLAM IV,827384,ESPORTS,2025-11-09T06:30:00Z,N/A,N/A,N/A,N/A
```

### Documentation

- `grid_data/WHAT_YOU_CAN_PULL.md` - Detailed API capabilities
- `grid_data/TITLE_ID_MAPPING.md` - Correct titleId mappings
- `grid_data/GRID_SUPPORT_SERIES_STATE_ISSUE.md` - API access issues

---

## 🚀 2. EVE Online Market Data (`eve_online_data/`)

**API:** [Mokaam.dk](https://mokaam.dk/)  
**Regions:** The Forge, Domain, Sinq Laison, Delve, and 7 more  
**Data:** Complete historic market statistics

### What You CAN Pull ✅

- Volume data (yesterday, week, month, quarter, year)
- Average prices (all timeframes)
- High/Low prices
- Market size (price × volume)
- VWAP (Volume-Weighted Average Price)
- 52-week highs/lows
- Standard deviations
- Order counts
- Spreads

### Usage

```bash
# Pull specific items (recommended)
cd /Users/jkang/Documents/vscode/e2e-flow
uv run eve_online_data/eve_market_pull.py

# Configure in eve_market_pull.py:
SELECTED_REGION = "forge"  # The Forge (Jita)
MODE = "specific"
TYPE_IDS = [44992, 34, 35, 36, 37, 38, 39, 40]  # PLEX + minerals
```

### Output Example

```csv
typeid,item_name,timestamp_pulled,last_data,vol_yesterday,vol_week,vol_month,avg_price_yesterday,avg_price_week,avg_price_month,...
44992,PLEX,2025-10-31 21:20:18,2025-10-30,0.0,0.0,0.0,5975000.0,5975000.0,5975000.0,...
34,Tritanium,2025-10-31 21:20:18,2025-10-30,3714217954.0,3714217954.0,4405645035.5,4.29,4.22,4.2,...
```

**Note:** `timestamp_pulled` is in UTC format (YYYY-MM-DD HH:MM:SS) and is Snowflake-compatible (TIMESTAMP_NTZ).

### Popular Items

- **44992** - PLEX
- **34** - Tritanium
- **35** - Pyerite
- **36** - Mexallon
- **37** - Isogen
- **38** - Nocxium
- **39** - Zydrine
- **40** - Megacyte

### Documentation

- `eve_online_data/README.md` - Complete usage guide
- API updates daily at 12:05 PM UTC

---

## 📊 Comparison

| Feature | GRID (Esports) | Mokaam (EVE Online) |
|---------|----------------|---------------------|
| **API Access** | Limited (metadata only) | Full (all market data) |
| **Authentication** | API key required | No auth required |
| **Rate Limiting** | Yes (tested limits) | Yes (403 if exceeded) |
| **Data Freshness** | Real-time | Daily (12:05 PM UTC) |
| **Use Cases** | Tournament calendars | Trading, market analysis |
| **Cost** | Free tier (limited) | Free (community project) |

---

## 🎯 Use Cases

### GRID Data

- **Tournament Tracking:** Monitor upcoming esports matches
- **Series Discovery:** Find series by game and tournament
- **Schedule Building:** Create tournament calendars
- **Metadata Analysis:** Study tournament patterns

### EVE Online Data

- **Market Analysis:** Track price trends
- **Trading Strategies:** Identify profitable items
- **Economic Research:** Study market behavior
- **Price Alerts:** Monitor specific items

---

## 📁 Project Structure

```text
/Users/jkang/Documents/vscode/e2e-flow/
├── grid_data/
│   ├── grid_data_pull.py          # Main GRID data puller
│   ├── find_dota2_series.py       # Find Dota 2 series IDs
│   ├── find_cs2_series.py         # Find CS2 series IDs
│   ├── WHAT_YOU_CAN_PULL.md       # API capabilities
│   ├── TITLE_ID_MAPPING.md        # Correct game IDs
│   └── *.csv                      # Generated data files
│
├── eve_online_data/
│   ├── eve_market_pull.py         # Main EVE data puller
│   ├── README.md                  # Complete guide
│   └── *.csv                      # Generated data files
│
└── DATA_PULLING_SUMMARY.md        # This file
```

---

## 🔧 Requirements

Both scripts use:

- Python 3.13
- `requests` library
- `uv` package manager

Install dependencies:

```bash
cd /Users/jkang/Documents/vscode/e2e-flow
uv sync
```

---

## 📝 Notes

### GRID API

- **Limited Access:** Current API key only has Central Data Feed access
- **Missing Features:** Teams, winners, scores require premium tier
- **Contact Support:** <support@grid.gg> to upgrade
- **Documentation Issues:** titleId mappings are incorrect in docs

### Mokaam API

- **Community Project:** Running on personal server
- **Best Practices:** Use comma-separated type IDs
- **Rate Limiting:** 403 status = wait 10-15 minutes
- **Contact:** IGN Mokaam Racor or Mokaam on Discord

---

## 🚦 Next Steps

### To Get More GRID Data

1. Contact GRID support: <support@grid.gg>
2. Request access to:
   - Series State API (match results)
   - File Download API (detailed play-by-play)
3. Upgrade to premium tier if needed

### To Expand EVE Data

1. Add more regions in `REGION_CONFIG`
2. Query type IDs: `get_type_ids()` function
3. Use `MODE = "all"` for complete datasets
4. Create custom filters for specific item categories

---

**Last Updated:** October 31, 2025
