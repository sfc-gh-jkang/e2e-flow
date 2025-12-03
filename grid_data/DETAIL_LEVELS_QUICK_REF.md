# Detail Levels - Quick Reference Card

## 📊 Quick Configuration Guide

Edit `grid_data_pull.py` **line 101**:

```python
DETAIL_LEVEL = "summary"  # or "games" or "full"
```

---

## 🎯 Three Levels Explained

### 1️⃣ SUMMARY (High Priority Data Only)
```python
DETAIL_LEVEL = "summary"
```

**What you get:**
- ✅ 1 CSV file
- ✅ 19 columns
- ✅ Team scores (NEW!)
- ✅ Series winners
- ✅ Games played count

**Example output:**
```csv
series_id,team_1_name,team_1_score,team_2_name,team_2_score,winner
2866787,L1ga Team,1,KalmyChata,2,KalmyChata
```

**Best for:** Quick standings, bracket updates, tournament results

**File size:** ~9 KB for 50 series

---

### 2️⃣ GAMES (High + Medium Priority Data)
```python
DETAIL_LEVEL = "games"
```

**What you get:**
- ✅ 2 CSV files (summary + games)
- ✅ Game-by-game scores
- ✅ Individual game winners
- ✅ Game IDs (UUIDs)

**Example games output:**
```csv
series_id,game_number,team_1_score,team_1_won,team_2_score,team_2_won
2866787,1,25,No,36,Yes
2866787,2,35,Yes,16,No
2866787,3,24,No,34,Yes
```

**Best for:** Match analysis, comeback tracking, close game detection

**File size:** ~30 KB for 50 series

---

### 3️⃣ FULL (All Priority Data)
```python
DETAIL_LEVEL = "full"  # DEFAULT
```

**What you get:**
- ✅ 3 CSV files (summary + games + players)
- ✅ Individual player stats
- ✅ Kills/deaths per game
- ✅ Player IDs

**Example players output:**
```csv
series_id,game_number,team_name,player_name,kills,deaths
2,1,DOTA-1,mks,22,7
2,1,DOTA-2,inYourdreaM,19,6
```

**Best for:** Player rankings, MVP tracking, K/D analytics

**File size:** ~200 KB for 50 series

---

## 📋 Comparison Table

| Feature | Summary | Games | Full |
|---------|---------|-------|------|
| **Files** | 1 | 2 | 3 |
| **Team Scores** | ✅ | ✅ | ✅ |
| **Game Details** | ❌ | ✅ | ✅ |
| **Player Stats** | ❌ | ❌ | ✅ |
| **Speed** | Fast | Fast | Fast* |
| **Size (50 series)** | ~9 KB | ~30 KB | ~200 KB |

*Same API calls for all levels - difference is only in local processing/CSV writes

---

## 💡 Recommendations by Use Case

| Use Case | Recommended Level |
|----------|-------------------|
| Tournament Standings | `"summary"` |
| Match Results | `"summary"` |
| Bracket Updates | `"summary"` |
| Game Analysis | `"games"` |
| Comeback Detection | `"games"` |
| Series Progression | `"games"` |
| Player Rankings | `"full"` |
| MVP Tracking | `"full"` |
| K/D Analytics | `"full"` |
| Talent Scouting | `"full"` |

---

## 🚀 Quick Commands

### Test with 2 series
```python
# In grid_data_pull.py
SPECIFIC_SERIES_IDS = ["2", "2866787"]
DETAIL_LEVEL = "full"  # Try all three levels
```

```bash
uv run grid_data/grid_data_pull.py
```

### Production: 50 recent completed series
```python
# In grid_data_pull.py
SPECIFIC_SERIES_IDS = None
QUERY_MODE = "smart"
NUM_SERIES = 50
DETAIL_LEVEL = "full"  # or "games" or "summary"
```

```bash
uv run grid_data/grid_data_pull.py
```

---

## 📊 What Each Level Captures

### NEW Fields in Summary Level
- `team_1_score` - Games won by team 1
- `team_2_score` - Games won by team 2

### NEW in Games Level
- `game_id` - Unique UUID for each game
- `game_number` - Sequence in series (1, 2, 3...)
- Per-game winners and scores

### NEW in Full Level  
- `player_id` - Unique player identifier
- `player_name` - Player name
- `kills` - Player kills in game
- `deaths` - Player deaths in game

---

## ⚠️ Important Notes

1. **All levels query the same data from API** - difference is what gets saved
2. **No performance difference** - same speed for all levels
3. **Backward compatible** - existing scripts work unchanged
4. **Default is "full"** - most comprehensive data
5. **Change anytime** - no migration needed

---

## 📚 More Info

- Complete Guide: `ENHANCED_DATA_GUIDE.md`
- Field Reference: `AVAILABLE_DATA_FIELDS.md`
- Quick Start: `QUICK_START.md`

---

**Last Updated:** November 3, 2025  
**Default:** `DETAIL_LEVEL = "full"`








