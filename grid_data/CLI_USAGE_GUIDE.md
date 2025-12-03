# GRID Data Puller - Command Line Interface Guide

## 🚀 Quick Start

The script now supports command line arguments! No need to edit Python code.

### Basic Usage

```bash
# Pull 50 CS2 series (default settings)
uv run grid_data/grid_data_pull.py --game cs2

# Pull 100 Dota 2 series
uv run grid_data/grid_data_pull.py --game dota2 --series 100

# Pull CS:GO with minimal data
uv run grid_data/grid_data_pull.py --game csgo --detail summary
```

---

## 📋 All Available Flags

### `--game` (Required for CLI mode)
**Choices:** `dota2`, `csgo`, `cs2`  
**Default:** Uses config value (dota2)  
**Description:** Which game to pull data for

```bash
uv run grid_data/grid_data_pull.py --game cs2
```

### `--series`
**Type:** Integer  
**Default:** 50 (from config)  
**Description:** Number of series to pull

```bash
uv run grid_data/grid_data_pull.py --game cs2 --series 100
```

### `--detail`
**Choices:** `summary`, `games`, `full`  
**Default:** `full` (from config)  
**Description:** Level of detail in output

- `summary` - Main CSV only (19 columns, team scores)
- `games` - Main CSV + games detail CSV  
- `full` - All 5 CSVs (series + games + players + teams + player summary)

```bash
uv run grid_data/grid_data_pull.py --game dota2 --detail games
```

### `--ids` (Optional)
**Type:** Comma-separated string  
**Default:** None (auto-query based on `--mode`)  
**Description:** Specific series IDs to query. If provided, bypasses auto-query and ignores `--mode`.

```bash
# Query specific series IDs (skips auto-query)
uv run grid_data/grid_data_pull.py --game cs2 --ids 123,456,789
```

**When to use:**
- You know exactly which series you want
- Analyzing specific matches/tournaments
- Testing with known series IDs

**When not to use:**
- You want the most recent data (omit --ids, use --mode instead)

### `--mode` (Optional, ignored if `--ids` is provided)
**Choices:** `smart`, `recent`  
**Default:** `smart` (from config)  
**Description:** How to auto-query series when `--ids` is NOT provided

**`smart` mode (DEFAULT - Recommended):**
- Finds most recent series WITH completed match data
- 100% success rate - all returned series have real match results
- Slower (~4 minutes for 50 series)
- Checks ~200 series to find 50 with data
- Skips future/scheduled matches automatically

**`recent` mode (Fast but may have incomplete data):**
- Gets the most recent series regardless of status
- Fast (~30 seconds for 50 series)
- May include future/scheduled matches with no data yet
- Some series might have `games_played=0`

```bash
# Smart mode (default) - all series have data
uv run grid_data/grid_data_pull.py --game dota2 --mode smart

# Recent mode - fast but may include future matches
uv run grid_data/grid_data_pull.py --game dota2 --mode recent
```

**When to use each:**
- **Use `smart`** - For analytics, ensuring all series have match data
- **Use `recent`** - For quick checks, tournament calendars, or when you want to see upcoming matches

---

## 🎯 Understanding Query Modes

### What are Query Modes?

Query modes determine **HOW** the script finds series to pull when you DON'T provide specific `--ids`.

### Comparison Table

| Feature | `smart` mode (Default) | `recent` mode |
|---------|----------------------|---------------|
| **Speed** | Slower (~4 min for 50) | Fast (~30 sec for 50) |
| **Data Quality** | 100% have match data | May have no data yet |
| **Use Case** | Analytics, historical data | Quick checks, calendars |
| **Series Checked** | ~200 to find 50 good ones | First 50 series found |
| **Future Matches** | Automatically skipped | Included |
| **Success Rate** | 100% (all have data) | Variable (some may be empty) |

### Visual Example

**Smart Mode:**
```
API has: [Future, Future, Completed✓, Future, Completed✓, Future, Completed✓, ...]
                      ↓                    ↓                    ↓
Returns: [Completed✓, Completed✓, Completed✓, ...] (50 series with data)
```

**Recent Mode:**
```
API has: [Future, Future, Completed✓, Future, Completed✓, Future, ...]
         ↓       ↓        ↓           ↓        ↓           ↓
Returns: [Future, Future, Completed✓, Future, Completed✓, Future, ...] (first 50)
```

### When to Use Each

**Use `smart` mode when:**
- ✅ You need guaranteed match data
- ✅ Building analytics dashboards
- ✅ Historical data collection
- ✅ Player performance analysis
- ✅ You can wait 3-5 minutes

**Use `recent` mode when:**
- ⚡ You need results quickly
- ⚡ Checking tournament schedules
- ⚡ Listing upcoming matches
- ⚡ You're okay with some empty series
- ⚡ You'll filter by `games_played > 0` later

**Use `--ids` when:**
- 🎯 You know exact series you need
- 🎯 Analyzing specific matches
- 🎯 Testing/debugging
- 🎯 Following up on specific tournaments

### Command Examples

```bash
# SMART: Get 50 series guaranteed to have data (slow but reliable)
uv run grid_data/grid_data_pull.py --game cs2 --mode smart --series 50

# RECENT: Get 50 most recent series fast (may include future matches)
uv run grid_data/grid_data_pull.py --game cs2 --mode recent --series 50

# SPECIFIC: Get exact series (fastest, bypasses search)
uv run grid_data/grid_data_pull.py --game cs2 --ids 100,200,300
```

---

## 💡 Common Usage Examples

### Example 1: Quick CS2 Pull
```bash
uv run grid_data/grid_data_pull.py --game cs2
```
**Result:** 5 CS2 CSV files with 50 series

### Example 2: Large Dota 2 Dataset
```bash
uv run grid_data/grid_data_pull.py --game dota2 --series 200 --detail full
```
**Result:** 5 Dota 2 CSV files with 200 series

### Example 3: Fast CS:GO Summary Only
```bash
uv run grid_data/grid_data_pull.py --game csgo --series 20 --detail summary
```
**Result:** 1 CS:GO CSV file with 20 series (no player/game details)

### Example 4: Specific Series Analysis
```bash
uv run grid_data/grid_data_pull.py --game cs2 --ids 2,2866787 --detail full
```
**Result:** 5 CSV files with data for 2 specific CS2 series

### Example 5: Recent Series (Fast Mode)
```bash
uv run grid_data/grid_data_pull.py --game dota2 --mode recent --series 30
```
**Result:** 30 most recent Dota 2 series (may include future/scheduled)

### Example 6: Comprehensive Multi-Game Pull
```bash
# Pull all 3 games
uv run grid_data/grid_data_pull.py --game dota2 --series 50
uv run grid_data/grid_data_pull.py --game csgo --series 50
uv run grid_data/grid_data_pull.py --game cs2 --series 50
```
**Result:** 15 CSV files total (5 per game)

---

## 📊 Output Files by Detail Level

### `--detail summary` (1 file)
```
cs2_series_summary_{timestamp}.csv
```
- 19 columns
- Series-level data with team scores
- ~9 KB for 50 series

### `--detail games` (2 files)
```
cs2_series_summary_{timestamp}.csv
cs2_series_summary_games_{timestamp}.csv
```
- Main CSV + game-by-game details
- ~30 KB for 50 series

### `--detail full` (5 files - DEFAULT)
```
cs2_series_summary_{timestamp}.csv
cs2_series_summary_games_{timestamp}.csv
cs2_series_summary_players_{timestamp}.csv
cs2_series_summary_teams_{timestamp}.csv
cs2_series_summary_player_summary_{timestamp}.csv
```
- Complete dataset with player stats
- ~200 KB for 50 series

---

## 🔧 Combining Flags

All flags can be combined:

```bash
# Pull 100 CS2 series with games detail in smart mode
uv run grid_data/grid_data_pull.py \
  --game cs2 \
  --series 100 \
  --detail games \
  --mode smart
```

```bash
# Analyze specific Dota 2 series with full player data
uv run grid_data/grid_data_pull.py \
  --game dota2 \
  --ids 1000,2000,3000 \
  --detail full
```

---

## ⚙️ Default Behavior (No Flags)

If you run without any flags:

```bash
uv run grid_data/grid_data_pull.py
```

It uses the config values from the Python file:
- Game: `dota2`
- Series: `50`
- Detail: `full`
- Mode: `smart`
- IDs: `None` (auto-query)

---

## 🆘 Getting Help

```bash
uv run grid_data/grid_data_pull.py --help
```

Shows all available options with descriptions.

---

## 📝 Player Data in All Outputs

Regardless of which game you choose, **player data** is included:

### In Players Detail CSV:
- ✅ player_id
- ✅ player_name
- ✅ team_id
- ✅ team_name
- ✅ kills, deaths (per game)

### In Player Summary CSV:
- ✅ player_id
- ✅ player_name
- ✅ team_id
- ✅ team_name
- ✅ Aggregated stats (total/avg kills, deaths, K/D)

### In Team Summary CSV:
- ✅ team_id
- ✅ team_name
- ✅ team_logo_url (from Central Data Feed!)
- ✅ Games won/lost, series count

All CSVs have proper IDs for joining!

---

## ⚡ Performance Tips

### For Speed
```bash
# Use recent mode + summary detail
uv run grid_data/grid_data_pull.py --game cs2 --mode recent --detail summary
```

### For Completeness
```bash
# Use smart mode + full detail
uv run grid_data/grid_data_pull.py --game cs2 --mode smart --detail full
```

### For Specific Analysis
```bash
# Pull exact series you need
uv run grid_data/grid_data_pull.py --game dota2 --ids 123,456
```

---

## 🎯 Typical Workflows

### Daily Tournament Tracking
```bash
# Pull latest 20 series each day
uv run grid_data/grid_data_pull.py --game cs2 --series 20 --mode smart
```

### Player Performance Analysis
```bash
# Get full player stats for last 100 matches
uv run grid_data/grid_data_pull.py --game dota2 --series 100 --detail full
```

### Team Scouting
```bash
# Get team data with logos
uv run grid_data/grid_data_pull.py --game cs2 --series 50 --detail full
# Teams CSV will have logos for dashboards
```

### Historical Data Collection
```bash
# Pull large datasets for all games
for game in dota2 csgo cs2; do
  uv run grid_data/grid_data_pull.py --game $game --series 200
done
```

---

## 🔗 Integration Examples

### Snowflake Upload
```bash
# Pull CS2 data
uv run grid_data/grid_data_pull.py --game cs2 --series 100 --detail full

# Upload CSVs to Snowflake
snowsql -f upload_cs2_data.sql
```

### Automated Cron Job
```bash
# Add to crontab for daily pulls
0 2 * * * cd /path/to/project && uv run grid_data/grid_data_pull.py --game cs2 --series 50
```

### Python Script Integration
```python
import subprocess

# Pull data programmatically
subprocess.run([
    "uv", "run", "grid_data/grid_data_pull.py",
    "--game", "cs2",
    "--series", "100",
    "--detail", "full"
])
```

---

## 📚 Related Documentation

- **Enhanced Data Guide:** `ENHANCED_DATA_GUIDE.md`
- **Available Fields:** `AVAILABLE_DATA_FIELDS.md`
- **Detail Levels:** `DETAIL_LEVELS_QUICK_REF.md`
- **Title ID Mapping:** `TITLE_ID_MAPPING.md`

---

**Last Updated:** November 3, 2025  
**Version:** 2.1 (CLI Support Added)

