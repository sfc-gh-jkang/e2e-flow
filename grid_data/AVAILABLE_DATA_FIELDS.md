# GRID Series State API - Available Data Fields

## 📊 Complete Field Reference

Based on testing with the Series State GraphQL API, here's what data is available:

---

## ✅ Currently Captured Fields

### **Series Level** (5 fields)
| Field | Type | Description | Currently Captured |
|-------|------|-------------|-------------------|
| `valid` | Boolean | Is the series state data valid? | ✅ Yes (internal check) |
| `updatedAt` | Timestamp | Last update time | ✅ Yes (internal use) |
| `format` | String | Match format (e.g., "best-of-3") | ✅ Yes → CSV |
| `started` | Boolean | Has the series started? | ✅ Yes → CSV |
| `finished` | Boolean | Is the series finished? | ✅ Yes → CSV |

### **Team Level** (4 fields)
| Field | Type | Description | Currently Captured |
|-------|------|-------------|-------------------|
| `id` | String | Unique team ID | ✅ Yes → CSV |
| `name` | String | Team name | ✅ Yes → CSV |
| `won` | Boolean | Has this team won the series? | ✅ Yes → CSV |
| `score` | Integer | Current series score | ❌ **NOT CAPTURED** |

### **Game Level** (4 fields)
| Field | Type | Description | Currently Captured |
|-------|------|-------------|-------------------|
| `id` | String | Unique game ID (UUID) | ❌ **NOT CAPTURED** |
| `sequenceNumber` | Integer | Game number in series (1, 2, 3...) | ✅ Yes (for count only) |
| `started` | Boolean | Has game started? | ✅ Yes (for filtering) |
| `finished` | Boolean | Is game finished? | ✅ Yes (for filtering) |

### **Game Team Level** (5 fields)
| Field | Type | Description | Currently Captured |
|-------|------|-------------|-------------------|
| `id` | String | Team ID | ❌ **NOT CAPTURED** |
| `name` | String | Team name | ❌ **NOT CAPTURED** |
| `won` | Boolean | Did team win this game? | ❌ **NOT CAPTURED** |
| `score` | Integer | Team score for this game | ❌ **NOT CAPTURED** |
| `players` | Array | Player statistics | ❌ **NOT CAPTURED** |

### **Player Level** (4 fields)
| Field | Type | Description | Currently Captured |
|-------|------|-------------|-------------------|
| `id` | String | Unique player ID | ❌ **NOT CAPTURED** |
| `name` | String | Player name | ❌ **NOT CAPTURED** |
| `kills` | Integer | Player kills in game | ❌ **NOT CAPTURED** |
| `deaths` | Integer | Player deaths in game | ❌ **NOT CAPTURED** |

---

## 🎯 Recommended Fields to Add

### **HIGH PRIORITY** - Series/Team Level

#### 1. **Team Score** (Series Level)
```python
# What it provides:
teams {
    score  # Current series score (e.g., 2 wins out of best-of-5)
}

# Example data:
Team 1: score = 1 (won 1 game so far)
Team 2: score = 0 (won 0 games so far)

# Why useful:
- Know current series standing
- Calculate games remaining
- Determine match progression
```

**CSV Impact:** Add `team_1_score` and `team_2_score` columns

---

### **MEDIUM PRIORITY** - Game-by-Game Details

#### 2. **Game IDs**
```python
games {
    id  # Unique identifier for each game
}

# Example: "474ba389-5b1d-4a91-ba3e-e96c9a5625a9"

# Why useful:
- Link to detailed game data
- Track individual game performance
- Reference specific games in series
```

#### 3. **Per-Game Winners**
```python
games {
    teams {
        won  # Which team won THIS specific game
        score  # Final score for THIS game
    }
}

# Example Game 1:
Team 1: won = True, score = 43
Team 2: won = False, score = 39

# Why useful:
- Game-by-game progression
- Analyze comebacks
- Score differentials
```

---

### **LOW PRIORITY** - Player Statistics

#### 4. **Player Data**
```python
games {
    teams {
        players {
            id      # Player ID
            name    # Player name
            kills   # Kills in this game
            deaths  # Deaths in this game
        }
    }
}

# Example:
Player "mks" (ID: 90541): 22 kills, 7 deaths

# Why useful:
- Player performance tracking
- MVP identification
- K/D ratios
- Individual player analytics
```

**Note:** This creates MASSIVE data expansion:
- 2 teams × 5 players × N games = A LOT of rows
- Consider separate CSV or database table
- May want player aggregates instead of per-game

---

## 📋 Current CSV Output (17 columns)

```csv
series_id,game_title,tournament,tournament_id,series_type,start_time,
team_1_name,team_1_id,team_2_name,team_2_id,
series_started,series_finished,series_format,
team_1_won,team_2_won,winner,games_played
```

---

## 🎯 Proposed Enhanced CSV Output

### **Option 1: Add Team Scores (19 columns)**
```csv
series_id,game_title,tournament,tournament_id,series_type,start_time,
team_1_name,team_1_id,team_1_score,    # ← NEW
team_2_name,team_2_id,team_2_score,    # ← NEW
series_started,series_finished,series_format,
team_1_won,team_2_won,winner,games_played
```

**Example:**
```csv
2866787,Dota 2,EPL S32,L1ga Team,53196,0,KalmyChata,53864,3,...
```
Shows KalmyChata won 3-0 (best-of-3)

---

### **Option 2: Add Game Details (Separate Table)**

**Series Summary CSV** (same as above with scores)

**Games Detail CSV** (new file: `{series_id}_games.csv`)
```csv
series_id,game_id,game_number,finished,
team_1_name,team_1_score,team_1_won,
team_2_name,team_2_score,team_2_won
```

**Example:**
```csv
2,474ba389-5b1d-4a91-ba3e-e96c9a5625a9,1,True,DOTA-1,43,True,DOTA-2,39,False
2,0bf7d681-07dd-4b9e-a31b-a03a41925d01,2,False,DOTA-1,12,False,DOTA-2,8,False
```

---

### **Option 3: Add Player Stats (Separate Table)**

**Players Detail CSV** (new file: `{series_id}_players.csv`)
```csv
series_id,game_id,game_number,team_name,
player_id,player_name,kills,deaths
```

**Example:**
```csv
2,474ba389-5b1d...,1,DOTA-1,90541,mks,22,7
2,474ba389-5b1d...,1,DOTA-1,90543,Salad,2,14
2,474ba389-5b1d...,1,DOTA-2,90548,inYourdreaM,19,6
...
```

---

## 💡 Recommendations by Use Case

### **Use Case 1: Tournament Results & Standings**
**Need:** Series winners, final scores  
**Add:** `team_1_score`, `team_2_score`  
**Complexity:** Low (2 fields)  
**CSV Size:** +2 columns

### **Use Case 2: Match Analysis & Comebacks**
**Need:** Game-by-game progression  
**Add:** Games detail table  
**Complexity:** Medium (separate CSV)  
**CSV Size:** New file, ~N rows per series

### **Use Case 3: Player Performance & Stats**
**Need:** Individual player data  
**Add:** Player detail table  
**Complexity:** High (10x data volume)  
**CSV Size:** New file, ~10×N rows per series

### **Use Case 4: Comprehensive Database**
**Need:** Everything  
**Add:** All three enhancements  
**Complexity:** High  
**CSV Size:** 3 files per pull

---

## 🔧 Implementation Difficulty

### **Easy - Team Scores** ⭐
- **Changes:** 2 lines in GraphQL query, 2 lines in extraction
- **Test time:** 1 minute
- **Value:** High (know final scores immediately)

### **Medium - Game Details** ⭐⭐
- **Changes:** New function to process games, new CSV
- **Test time:** 5 minutes
- **Value:** Medium (useful for analysis)

### **Hard - Player Stats** ⭐⭐⭐
- **Changes:** New data structure, nested loops, large files
- **Test time:** 15 minutes
- **Value:** Low-Medium (niche use case)

---

## 📊 Data Volume Impact

### **Current:**
- 50 series = 50 rows
- File size: ~8KB

### **With Team Scores:**
- 50 series = 50 rows
- File size: ~9KB (+12%)

### **With Game Details:**
- 50 series × 3 avg games = 150 rows
- File size: ~25KB (3× increase)

### **With Player Stats:**
- 50 series × 3 games × 10 players = 1,500 rows
- File size: ~150KB (18× increase)

---

## ✅ Quick Wins - Add These First

1. **`team_1_score` and `team_2_score`** - Minimal effort, high value
2. **Game count verification** - Already have, just need to validate

---

## 🎯 Next Steps

**Recommended Implementation Order:**

1. ✅ **Phase 1:** Add team scores (EASY, HIGH VALUE)
   - Update GraphQL query to include `score`
   - Add 2 columns to CSV
   - Test with 5 series

2. 📊 **Phase 2:** Add game details (MEDIUM, MEDIUM VALUE)
   - Create new function for game processing
   - Generate separate games CSV
   - Optional: Add as configuration flag

3. 🎮 **Phase 3:** Add player stats (HARD, SPECIALIZED)
   - Only if explicitly needed
   - Consider separate script
   - May want to aggregate (avg K/D per series)

---

## 📝 Fields NOT Available (Tested)

These fields were tested but are NOT supported by the API:

- ❌ `teams.side` - Team side (Radiant/Dire, CT/T)
- ❌ `players.assists` - Player assists
- ❌ `players.netWorth` - Player gold/economy (mentioned in example but not working)
- ❌ `players.money` - Current player money
- ❌ `players.position` - Player map position
- ❌ Series-level `deletedAt` - Deletion timestamp
- ❌ Series-level `startTimeActual` - Actual start time

**Note:** The example query in the GRID documentation includes some fields that don't actually work (like `position`, `netWorth`, `money`). The API is simpler than documented.

---

## 🔗 References

- **Series State GraphQL Endpoint:** `https://api-op.grid.gg/live-data-feed/series-state/graphql`
- **Test Script:** `grid_data/explore_available_fields.py`
- **Current Implementation:** `grid_data/grid_data_pull.py`

---

**Last Updated:** November 3, 2025  
**Test Series:** ID "2" (Dota 2 test series with live data)








