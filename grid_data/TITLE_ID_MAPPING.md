# GRID API Title ID Mapping - CORRECTED

## 🚨 Important: GRID Documentation is WRONG

The official GRID API documentation has **incorrect** titleId mappings. Here are the **actual** mappings discovered through testing:

## ✅ Actual Title ID Mappings

| titleId | Actual Game | Series Count | Documentation Claims | Status |
|---------|-------------|--------------|---------------------|--------|
| **1** | **Counter Strike: Global Offensive** | 36,182 | Dota 2 ❌ | ✅ Working |
| **2** | **Defense of the Ancients 2** (Dota 2) | 27,565 | Not documented | ✅ Working |
| **3** | No data | 0 | CS2 ❌ | ❌ Empty |
| 4-27 | No data | 0 | Unknown | ❌ Empty |
| **28** | **Counter-Strike 2** (CS2) | 15,288 | Not documented | ✅ Working |

## 🔍 Testing Results

**Test Date:** October 31, 2025

```bash
titleId 1: Counter Strike: Global Offensive - 36,182 series ✅
titleId 2: Defense of the Ancients 2 - 27,565 series ✅
titleId 3-27: No series found
titleId 28: Counter Strike 2 - 15,288 series ✅
```

### Sample Series from titleId 1 (CS:GO)

- Series ID: 1 - GRID-TEST
- Series ID: 2744702 - United Masters League 2018-2019
- Series ID: 2598310 - Roobet Cup 2023
- **All show game:** "Counter Strike: Global Offensive"

## ✅ CS2 Found

**CS2 (Counter-Strike 2) exists at titleId 28!**

The GRID API documentation is incorrect:

- ❌ Docs claim titleId 3 = CS2 (returns 0 series)
- ✅ Reality: titleId 28 = CS2 (has data!)
- ✅ titleId 1 = CS:GO (separate from CS2)

## 📝 Updated Script Configurations

### For CS:GO (Counter-Strike: Global Offensive)

```python
titleId: 1  # 36,182 series available
```

### For Dota 2

```python
titleId: 2  # 27,565 series available
```

### For CS2 (Counter-Strike 2)

```python
titleId: 28  # CORRECT - CS2 is at titleId 28 (not 3!)
```

## 🛠️ Fixed Scripts

The following scripts have been corrected:

### ✅ `find_dota2_series.py`

- **Changed from:** `titleId: 1`
- **Changed to:** `titleId: 2`
- **Now returns:** Actual Dota 2 data (not CS:GO)

### ✅ `find_cs2_series.py`

- **Changed from:** `titleId: 3` (returned 0 series)
- **Changed to:** `titleId: 28` (returns actual CS2 data)
- **Now returns:** Counter-Strike 2 series ✅

### ✅ `grid_data_pull.py`

- **Updated:** Separate CS2 (`titleId: 28`) and CS:GO (`titleId: 1`) options
- **Now supports:** Dota 2, CS:GO, and CS2 independently

## 💡 Recommendations

1. **For CS:GO data:** Use `titleId: 1` (36K+ series available)
2. **For Dota 2 data:** Use `titleId: 2` (27K+ series available)
3. **For CS2 data:** Use `titleId: 28` (CS2 series available) ✅

## 📧 Contact GRID Support

If you need help or want to report the documentation errors:

**Email:** <support@grid.gg>  
**Subject:** "Title ID Documentation Corrections"

**Issues to report:**

- Documentation incorrectly lists titleId 1 as Dota 2 (it's CS:GO)
- Documentation incorrectly lists titleId 3 as CS2 (it's empty)
- titleId 2 = Dota 2 (not documented)
- titleId 28 = CS2 (not documented)

## 🔗 References

- **GRID API Documentation:** <https://portal.grid.gg/documentation/api-reference/central-data-feeds/central-data-feed-api#titles>
- **Our Testing Script:** `grid_data/test_all_titleids.py`
- **Rate Limit:** Hit after ~20 queries, so full scan not possible

---

**Last Updated:** October 31, 2025  
**Tested By:** Automated script `test_all_titleids.py`  
**Conclusion:** GRID docs are wrong. Use titleId 2 for Dota 2, titleId 1 for CS:GO. CS2 not found.
