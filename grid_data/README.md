# GRID Data Puller

Pull esports data (Dota 2, CS:GO, CS2) from the GRID API with complete player and team statistics.

## 🚀 Quick Start

```bash
# Pull 50 CS2 series with full player data
uv run grid_data/grid_data_pull.py --game cs2

# Pull 100 Dota 2 series
uv run grid_data/grid_data_pull.py --game dota2 --series 100

# Get help
uv run grid_data/grid_data_pull.py --help
```

## 📊 What You Get

Running the script generates **5 CSV files** (with `--detail full`, the default):

1. **Series Summary** - Match results, team scores, winners
2. **Games Detail** - Game-by-game breakdown
3. **Players Detail** - Per-game player stats (kills, deaths)
4. **Team Summary** - Team aggregates + logos from API
5. **Player Summary** - Player aggregates (K/D ratios, averages)

All CSVs include proper IDs (`player_id`, `team_id`) for joining!

## 🎮 Supported Games

- **Dota 2** (`--game dota2`) - 27,565+ series
- **CS:GO** (`--game csgo`) - 36,182+ series  
- **CS2** (`--game cs2`) - 15,000+ series

## 📋 Command Line Options

```bash
--game {dota2,csgo,cs2}        # Which game to pull
--series NUMBER                # How many series (default: 50)
--detail {summary,games,full}  # Detail level (default: full)
--ids ID1,ID2,ID3             # Specific series IDs (optional)
--mode {smart,recent}          # Query mode (default: smart)
```

### Query Modes

- **`smart`** (default) - Finds series WITH completed match data (slower, 100% success)
- **`recent`** - Gets most recent series fast (may include future matches with no data)

## 📚 Documentation Files

| File | Description |
|------|-------------|
| **CLI_USAGE_GUIDE.md** | Complete command line interface guide |
| **ENHANCED_DATA_GUIDE.md** | Comprehensive data guide with examples |
| **AVAILABLE_DATA_FIELDS.md** | All available fields reference |
| **DETAIL_LEVELS_QUICK_REF.md** | Quick reference card |
| **QUICK_START.md** | Quick start examples |
| **TITLE_ID_MAPPING.md** | Game title ID mappings (important!) |

## 💡 Common Examples

### Pull CS2 Data
```bash
uv run grid_data/grid_data_pull.py --game cs2
```

### Pull All 3 Games
```bash
uv run grid_data/grid_data_pull.py --game dota2
uv run grid_data/grid_data_pull.py --game csgo
uv run grid_data/grid_data_pull.py --game cs2
```

### Specific Series Analysis
```bash
uv run grid_data/grid_data_pull.py --game cs2 --ids 123,456,789
```

### Fast Mode (Quick Checks)
```bash
uv run grid_data/grid_data_pull.py --game dota2 --mode recent --series 20
```

## 🔧 Setup

1. Install dependencies:
```bash
pip install requests python-dotenv
```

2. Set up `.env` file in project root:
```
GRID_DATA_API_KEY=your_api_key_here
```

3. Run the script!

## 📊 Player Data Included

All outputs include comprehensive player data:

- ✅ `player_id` - For joining
- ✅ `player_name` - In-game names
- ✅ `team_id` - For joining with teams
- ✅ `team_name` - Team names
- ✅ `kills`, `deaths` - Per-game stats
- ✅ `kd_ratio`, `avg_kills`, `avg_deaths` - Aggregated stats

**Team data includes:**
- ✅ `team_id` - For joining
- ✅ `team_name` - Team names
- ✅ `team_logo_url` - Logo URLs from GRID API
- ✅ `games_won`, `games_lost` - Performance stats

## ⚠️ Known Limitations

- **No demographic data** - Age, nationality, gender not available without higher API tier
- **Player metadata limited** - Only IDs and nicknames from Central Data Feed
- **File Download API unavailable** - No detailed play-by-play data

See `AVAILABLE_DATA_FIELDS.md` for complete field reference.

## 🎯 Data Quality

- **Smart mode** - 100% of series have completed match data
- **All CSVs have proper foreign keys** for joining
- **Team logos** fetched from Central Data Feed API
- **Player stats** calculated and aggregated automatically

## 🔗 Output Files Example

After running with `--game cs2 --series 50`:
```
cs2_series_summary_20251103_120000.csv
cs2_series_summary_games_20251103_120000.csv
cs2_series_summary_players_20251103_120000.csv
cs2_series_summary_teams_20251103_120000.csv
cs2_series_summary_player_summary_20251103_120000.csv
```

All with timestamps for versioning.

## 📖 More Information

- **Full CLI guide:** `CLI_USAGE_GUIDE.md`
- **Data fields reference:** `AVAILABLE_DATA_FIELDS.md`
- **Enhanced guide:** `ENHANCED_DATA_GUIDE.md`

## 🆘 Getting Help

```bash
uv run grid_data/grid_data_pull.py --help
```

---

**Last Updated:** November 3, 2025  
**Version:** 2.1 (CLI Support + Team/Player Summaries)








