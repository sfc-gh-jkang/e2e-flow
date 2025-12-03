"""
GRID Game Series Data Puller

✅ NOW WORKING: This script pulls METADATA + SERIES STATE DATA
✅ SMART MODE (DEFAULT): Automatically finds series with completed match data!

Your API key has access to:
✅ Central Data Feed API - Series metadata (tournament names, series IDs, start times, etc.)
✅ Series State API (GraphQL) - Teams, scores, winners, match status
❌ File Download API - Returns 403 (no detailed play-by-play data)

🎯 SMART MODE (Default):
- Intelligently searches for the most recent series WITH completed data
- Skips future/scheduled series automatically
- 100% success rate - all returned series have real match results
- Checks ~200 series to find 50 with data (~4 minutes)
- Uses cursor-based pagination for efficiency

This script pulls:
- Series metadata from Central Data Feed API
- Series state (teams, scores, winners) from Series State GraphQL API
- Outputs CSV with complete match results (17 columns)

Supports:
- Dota 2 (titleId: 2) - 27,565+ series available ✅
- CS:GO (titleId: 1) - 36,182+ series available ✅
- CS2 (titleId: 28) - CS2 series available ✅

Configuration:
- QUERY_MODE = "smart" (default) - Find series with data
- QUERY_MODE = "recent" - Get recent series (fast but may be empty)
- SPECIFIC_SERIES_IDS = ["2", ...] - Query specific series IDs

⚠️  NOTE: GRID API documentation has incorrect titleId mappings!
- Docs say titleId 1 = Dota 2 (WRONG - it's CS:GO)
- Docs say titleId 3 = CS2 (WRONG - returns 0 series, actual CS2 is titleId 28)
- See TITLE_ID_MAPPING.md for full details

GraphQL Series State Endpoint: https://api-op.grid.gg/live-data-feed/series-state/graphql
"""

import os
import requests
from dotenv import load_dotenv
import json
import csv
from datetime import datetime
import time
import argparse
import logging

load_dotenv()

GRID_API_KEY = os.getenv("GRID_DATA_API_KEY")
GRAPHQL_ENDPOINT = "https://api-op.grid.gg/central-data/graphql"
SERIES_STATE_GRAPHQL_ENDPOINT = "https://api-op.grid.gg/live-data-feed/series-state/graphql"
CENTRAL_DATA_GRAPHQL_ENDPOINT = "https://api-op.grid.gg/central-data/graphql"

# ============================================================================
# CONFIGURATION
# ============================================================================
GAME_CONFIG = {
    "dota2": {
        "title_id": 2,  # CORRECTED: titleId 2 is Dota 2 (not 1!)
        "name": "Dota 2",
        "filename": "dota2_series_summary"
    },
    "csgo": {
        "title_id": 1,  # CORRECTED: titleId 1 is CS:GO (not Dota 2!)
        "name": "CS:GO",
        "filename": "csgo_series_summary"
    },
    "cs2": {
        "title_id": 28,  # CORRECTED: titleId 28 is CS2 (not 3!)
        "name": "CS2",
        "filename": "cs2_series_summary"
    }
}

# SELECT GAME: "dota2", "csgo", or "cs2"
SELECTED_GAME = "dota2"  # Change to "csgo" (36K+ series) or "cs2" (15K+ series)

# SERIES IDS (Optional): Specify series IDs to query, or set to None to auto-query
# Example: ["2", "100", "200"] for specific series, or None for auto-query
# Note: Recent/future series may not have state data. Series "2" is a test series with live data.
SPECIFIC_SERIES_IDS = None  # Set to list of series IDs or None to auto-query

# QUERY MODE: How to find series
# "smart" - Find most recent series with completed data (DEFAULT, slower but better results)
# "recent" - Get most recent series regardless of completion status (faster but may have no data)
QUERY_MODE = "smart"

# NUMBER OF SERIES: How many series to find (if SPECIFIC_SERIES_IDS is None)
NUM_SERIES = 50

# MAX SERIES TO CHECK: When in "smart" mode, max series to check before stopping
# (prevents infinite loops if there are no completed series)
# Increase this if you're not getting enough series
MAX_SERIES_TO_CHECK = 2000  # Increased from 500 to find more completed series

# DETAIL LEVEL: How much data to export
# "summary" - Main CSV only with team scores (19 columns)
# "games" - Main CSV + separate games detail CSV
# "full" - Main CSV + games CSV + players CSV (most detailed)
DETAIL_LEVEL = "full"

# EXCLUDED TOURNAMENTS: Tournament names to filter out (e.g., test data)
# Series from tournaments containing these strings will be excluded from results
EXCLUDED_TOURNAMENTS = ["GRID-TEST"]  # Add more strings to filter additional tournaments

CONFIG = {
    "api_key": GRID_API_KEY,
    "game": SELECTED_GAME,
    "specific_series_ids": SPECIFIC_SERIES_IDS,
    "query_mode": QUERY_MODE,
    "num_series": NUM_SERIES,
    "max_series_to_check": MAX_SERIES_TO_CHECK,
    "detail_level": DETAIL_LEVEL,
    "excluded_tournaments": EXCLUDED_TOURNAMENTS,
    "include_date_in_file_name": True,
    "output_directory": "grid_data_pulled"  # Directory to save all CSV files
}


def setup_logging(log_level=logging.INFO, log_file=None):
    """
    Configure logging with console and optional file output
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs to
    """
    # Create formatter with timestamp in UTC
    formatter = logging.Formatter(
        fmt='%(asctime)s UTC %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Configure formatter to use UTC
    formatter.converter = time.gmtime
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logging.info(f"📝 Logging to file: {log_file}")


def is_excluded_tournament(tournament_name):
    """Check if tournament should be excluded based on filter list"""
    excluded = CONFIG.get("excluded_tournaments", [])
    for excluded_str in excluded:
        if excluded_str in tournament_name:
            return True
    return False


def get_output_directory():
    """
    Get the output directory path and create it if it doesn't exist
    Returns the output directory path
    """
    output_dir = CONFIG.get("output_directory", ".")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_base_filename():
    """
    Get the base filename for the current game selection
    Returns the base filename (e.g., "dota2_series_summary", "cs2_series_summary")
    """
    current_game = CONFIG.get("game", "dota2")
    return GAME_CONFIG[current_game]["filename"]


def build_filename(base_filename, suffix="", extension="csv"):
    """
    Build a filename with optional timestamp and suffix
    
    Args:
        base_filename: Base name for the file
        suffix: Optional suffix to add before timestamp (e.g., "_games", "_players")
        extension: File extension (default: "csv")
    
    Returns:
        Full file path in the output directory
    """
    output_dir = get_output_directory()
    
    # Add suffix if provided
    filename = f"{base_filename}{suffix}"
    
    # Add timestamp if configured
    if CONFIG.get("include_date_in_file_name", True):
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{date_str}"
    
    # Add extension and prepend output directory
    filename = f"{filename}.{extension}"
    return os.path.join(output_dir, filename)


def save_csv_file(data, filename, fieldnames, data_type="data"):
    """
    Generic CSV writing function with error handling
    
    Args:
        data: List of dictionaries to write
        filename: Full file path
        fieldnames: List of column names
        data_type: Description of data for logging (e.g., "games", "players")
    
    Returns:
        Filename if successful, None if failed
    """
    if not data:
        logging.warning(f"   No {data_type} to save")
        return None
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            if isinstance(data, list):
                writer.writerows(data)
            else:
                writer.writerow(data)
        
        logging.info(f"   ✅ Saved {len(data) if isinstance(data, list) else 1} {data_type} to {filename}")
        return filename
    except Exception as e:
        logging.error(f"   ❌ Error saving {data_type} CSV: {e}")
        return None


def get_series_ids(game_key, num_series=50):
    """
    Query for recent series using Central Data Feed API
    Filters out excluded tournaments (configured in EXCLUDED_TOURNAMENTS)
    
    Args:
        game_key: Game configuration key ("dota2", "csgo", "cs2")
        num_series: Number of series to retrieve (after filtering)
    
    Returns list of series with IDs and metadata
    """
    game_config = GAME_CONFIG[game_key]
    game_name = game_config["name"]
    title_id = game_config["title_id"]
    
    # Request 2x series to account for excluded tournaments that will be filtered out
    api_request_count = num_series * 2
    
    logging.info(f"🔍 Querying Central Data Feed API for {num_series} most recent {game_name} series...")
    logging.info(f"   (Requesting {api_request_count} to account for excluded tournament filtering)")
    
    query = f"""
    {{
      allSeries(
        first: {api_request_count},
        filter: {{
          titleId: {title_id}
        }}
        orderBy: StartTimeScheduled
        orderDirection: DESC
      ) {{
        totalCount
        edges {{
          node {{
            id
            title {{
              id
              name
            }}
            tournament {{
              id
              name
            }}
            type
            startTimeScheduled
          }}
        }}
      }}
    }}
    """
    
    headers = {
        "x-api-key": GRID_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            GRAPHQL_ENDPOINT,
            headers=headers,
            json={"query": query},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "errors" in data:
                logging.error(f"❌ GraphQL errors: {data['errors']}")
                return []
            
            all_series = data.get("data", {}).get("allSeries", {})
            total_count = all_series.get("totalCount", 0)
            edges = all_series.get("edges", [])
            
            logging.info(f"✅ Retrieved {len(edges)} series from API (out of {total_count} total)")
            
            series_list = []
            filtered_count = 0
            for edge in edges:
                node = edge["node"]
                tournament_name = node.get("tournament", {}).get("name", "Unknown")
                
                # Skip excluded tournaments (e.g., test data)
                if is_excluded_tournament(tournament_name):
                    filtered_count += 1
                    continue
                
                # Stop if we have enough non-test series
                if len(series_list) >= num_series:
                    break
                
                series_list.append({
                    "id": node["id"],
                    "title": node.get("title", {}).get("name", "Unknown"),
                    "tournament": tournament_name,
                    "tournament_id": node.get("tournament", {}).get("id", "N/A"),
                    "type": node.get("type", "Unknown"),
                    "start_time": node.get("startTimeScheduled", "N/A"),
                    "team_1_name": "N/A",  # Teams/winner not available in Central Data Feed
                    "team_1_id": "N/A",
                    "team_2_name": "N/A",
                    "team_2_id": "N/A"
                })
            
            if filtered_count > 0:
                excluded_names = ", ".join(CONFIG.get("excluded_tournaments", []))
                logging.info(f"🔍 Filtered out {filtered_count} excluded series ({excluded_names})")
            logging.info(f"✅ Returning {len(series_list)} series")
            
            return series_list
        else:
            logging.error(f"❌ API Error: {response.status_code}")
            return []
            
    except Exception as e:
        logging.error(f"❌ Error getting series IDs: {e}")
        return []


def get_series_state(series_id, verbose=True):
    """
    Query Series State API using the correct GraphQL endpoint
    Returns series state data including teams, scores, and match status
    
    Args:
        series_id: Series ID to query
        verbose: If True, log errors. If False, silently return None on error.
    """
    
    query = """
    query GetSeriesState($seriesId: ID!) {
        seriesState(id: $seriesId) {
            valid
            updatedAt
            format
            started
            finished
            teams {
                id
                name
                won
                score
            }
            games(filter: { started: true }) {
                id
                sequenceNumber
                started
                startedAt
                finished
                finishedAt
                map {
                    id
                    name
                }
                teams {
                    id
                    name
                    side
                    won
                    score
                    players {
                        id
                        name
                        kills
                        deaths
                        netWorth
                        money
                        position {
                            x
                            y
                        }
                    }
                }
            }
        }
    }
    """
    
    headers = {
        "x-api-key": GRID_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            SERIES_STATE_GRAPHQL_ENDPOINT,
            headers=headers,
            json={
                "query": query,
                "variables": {"seriesId": str(series_id)}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if "errors" in data:
                if verbose:
                    logging.debug(f"   GraphQL errors for series {series_id}: {data['errors']}")
                return None
            
            series_state = data.get("data", {}).get("seriesState")
            
            if series_state:
                return series_state
            else:
                if verbose:
                    logging.debug(f"   No series state data for series {series_id}")
                return None
        else:
            if verbose:
                logging.debug(f"   Series State API error for {series_id}: {response.status_code}")
            return None
            
    except Exception as e:
        if verbose:
            logging.debug(f"   Exception getting series state for {series_id}: {e}")
        return None


def get_completed_series_with_state(game_key, num_series=50, max_to_check=500):
    """
    Intelligently find the most recent series that have completed and have state data.
    
    This function queries batches of series from Central Data Feed and checks each one
    for valid state data, continuing until it finds the requested number of completed series.
    
    Args:
        game_key: Game configuration key ("dota2", "csgo", "cs2")
        num_series: Number of completed series to find (default: 50)
        max_to_check: Maximum number of series to check before stopping (default: 500)
    
    Returns:
        List of series with metadata that have valid state data
    """
    game_config = GAME_CONFIG[game_key]
    game_name = game_config["name"]
    title_id = game_config["title_id"]
    
    logging.info(f"🔍 Smart Query: Finding {num_series} most recent {game_name} series WITH completed data...")
    logging.info(f"   This will check series until {num_series} with state data are found (max: {max_to_check})")
    
    completed_series = []
    checked_count = 0
    batch_size = 50  # Max allowed by GRID API
    cursor = None
    batch_num = 1
    
    while len(completed_series) < num_series and checked_count < max_to_check:
        # Query a batch of series using cursor-based pagination
        logging.info(f"   📊 Querying batch {batch_num} ({batch_size} series)...")
        
        # Build query with cursor if we have one
        after_clause = f', after: "{cursor}"' if cursor else ''
        
        query = f"""
        {{
          allSeries(
            first: {batch_size}{after_clause},
            filter: {{
              titleId: {title_id}
            }}
            orderBy: StartTimeScheduled
            orderDirection: DESC
          ) {{
            totalCount
            pageInfo {{
              hasNextPage
              endCursor
            }}
            edges {{
              cursor
              node {{
                id
                title {{
                  name
                }}
                tournament {{
                  name
                  id
                }}
                type
                startTimeScheduled
              }}
            }}
          }}
        }}
        """
        
        headers = {
            "x-api-key": GRID_API_KEY,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                GRAPHQL_ENDPOINT,
                headers=headers,
                json={"query": query},
                timeout=10
            )
            
            if response.status_code != 200:
                logging.error(f"❌ API Error: {response.status_code}")
                break
            
            data = response.json()
            
            if "errors" in data:
                logging.error(f"❌ GraphQL errors: {data['errors']}")
                break
            
            all_series = data.get("data", {}).get("allSeries", {})
            edges = all_series.get("edges", [])
            page_info = all_series.get("pageInfo", {})
            
            if not edges:
                logging.warning(f"   ⚠️  No more series found in batch {batch_num}")
                break
            
            # Check each series in this batch for state data
            for edge in edges:
                if len(completed_series) >= num_series:
                    break
                
                if checked_count >= max_to_check:
                    break
                
                node = edge["node"]
                series_id = node["id"]
                checked_count += 1
                
                # Check if this series has state data (without verbose logging)
                series_state = get_series_state(series_id, verbose=False)
                
                if series_state and series_state.get("valid"):
                    # Check if it's actually finished or has started
                    if series_state.get("finished") or series_state.get("started"):
                        tournament_name = node.get("tournament", {}).get("name", "Unknown")
                        
                        # Skip excluded tournaments (e.g., test data)
                        if is_excluded_tournament(tournament_name):
                            continue
                        
                        completed_series.append({
                            "id": series_id,
                            "title": node.get("title", {}).get("name", "Unknown"),
                            "tournament": tournament_name,
                            "tournament_id": node.get("tournament", {}).get("id", "N/A"),
                            "type": node.get("type", "Unknown"),
                            "start_time": node.get("startTimeScheduled", "N/A"),
                            "team_1_name": "N/A",
                            "team_1_id": "N/A",
                            "team_2_name": "N/A",
                            "team_2_id": "N/A"
                        })
                        
                        if len(completed_series) % 10 == 0:
                            logging.info(f"   ✅ Found {len(completed_series)}/{num_series} series with data (checked {checked_count} series)...")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            
            # Check if there are more pages
            if not page_info.get("hasNextPage"):
                logging.info(f"   ℹ️  Reached end of available series")
                break
            
            # Get cursor for next page
            cursor = page_info.get("endCursor")
            batch_num += 1
            
            # Small delay between batches
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f"❌ Error querying batch: {e}")
            break
    
    logging.info(f"✅ Smart Query complete: Found {len(completed_series)} series with data (checked {checked_count} total)")
    
    if len(completed_series) < num_series:
        logging.warning(f"⚠️  Only found {len(completed_series)}/{num_series} requested series")
        if checked_count >= max_to_check:
            logging.warning(f"   Reached max check limit of {max_to_check} series")
    
    return completed_series


def create_summary(series_metadata, series_state=None):
    """
    Create summary from metadata and series state (if available)
    Returns a dict with all available information
    """
    summary = {
        "series_id": series_metadata["id"],
        "game_title": series_metadata["title"],
        "tournament": series_metadata["tournament"],
        "tournament_id": series_metadata["tournament_id"],
        "series_type": series_metadata["type"],
        "start_time": series_metadata["start_time"],
        "team_1_name": "N/A",
        "team_1_id": "N/A",
        "team_1_score": 0,
        "team_2_name": "N/A",
        "team_2_id": "N/A",
        "team_2_score": 0,
        "series_started": "N/A",
        "series_finished": "N/A",
        "series_format": "N/A",
        "team_1_won": "N/A",
        "team_2_won": "N/A",
        "winner": "N/A",
        "games_played": 0
    }
    
    # Add series state data if available
    if series_state and series_state.get("valid"):
        teams = series_state.get("teams", [])
        
        if len(teams) >= 1:
            summary["team_1_name"] = teams[0].get("name", "N/A")
            summary["team_1_id"] = teams[0].get("id", "N/A")
            summary["team_1_score"] = teams[0].get("score", 0)
            summary["team_1_won"] = teams[0].get("won", False)
        
        if len(teams) >= 2:
            summary["team_2_name"] = teams[1].get("name", "N/A")
            summary["team_2_id"] = teams[1].get("id", "N/A")
            summary["team_2_score"] = teams[1].get("score", 0)
            summary["team_2_won"] = teams[1].get("won", False)
        
        summary["series_started"] = "Yes" if series_state.get("started") else "No"
        summary["series_finished"] = "Yes" if series_state.get("finished") else "No"
        summary["series_format"] = series_state.get("format", "N/A")
        
        # Determine winner
        if summary["series_finished"] == "Yes":
            if summary["team_1_won"] > summary["team_2_won"]:
                summary["winner"] = summary["team_1_name"]
            elif summary["team_2_won"] > summary["team_1_won"]:
                summary["winner"] = summary["team_2_name"]
            else:
                summary["winner"] = "Draw"
        
        # Count games
        games = series_state.get("games", [])
        summary["games_played"] = len(games)
    
    return summary


def extract_games_data(series_id, series_state, series_metadata):
    """
    Extract game-by-game details from series state
    Returns list of game dictionaries
    """
    games_data = []
    
    if not series_state or not series_state.get("valid"):
        return games_data
    
    games = series_state.get("games", [])
    
    for game in games:
        game_teams = game.get("teams", [])
        
        # Extract map data
        map_data = game.get("map", {})
        map_id = map_data.get("id", "N/A") if map_data else "N/A"
        map_name = map_data.get("name", "N/A") if map_data else "N/A"
        
        game_record = {
            "series_id": series_id,
            "game_id": game.get("id", "N/A"),
            "game_number": game.get("sequenceNumber", 0),
            "game_started": "Yes" if game.get("started") else "No",
            "game_started_at": game.get("startedAt", "N/A"),
            "game_finished": "Yes" if game.get("finished") else "No",
            "game_finished_at": game.get("finishedAt", "N/A"),
            "map_id": map_id,
            "map_name": map_name,
            "team_1_name": game_teams[0].get("name", "N/A") if len(game_teams) > 0 else "N/A",
            "team_1_id": game_teams[0].get("id", "N/A") if len(game_teams) > 0 else "N/A",
            "team_1_side": game_teams[0].get("side", "N/A") if len(game_teams) > 0 else "N/A",
            "team_1_score": game_teams[0].get("score", 0) if len(game_teams) > 0 else 0,
            "team_1_won": "Yes" if (len(game_teams) > 0 and game_teams[0].get("won")) else "No",
            "team_2_name": game_teams[1].get("name", "N/A") if len(game_teams) > 1 else "N/A",
            "team_2_id": game_teams[1].get("id", "N/A") if len(game_teams) > 1 else "N/A",
            "team_2_side": game_teams[1].get("side", "N/A") if len(game_teams) > 1 else "N/A",
            "team_2_score": game_teams[1].get("score", 0) if len(game_teams) > 1 else 0,
            "team_2_won": "Yes" if (len(game_teams) > 1 and game_teams[1].get("won")) else "No",
            "tournament": series_metadata.get("tournament", "N/A"),
            "game_title": series_metadata.get("title", "N/A")
        }
        
        games_data.append(game_record)
    
    return games_data


def extract_players_data(series_id, series_state, series_metadata):
    """
    Extract player statistics from all games in the series
    Returns list of player dictionaries
    """
    players_data = []
    
    if not series_state or not series_state.get("valid"):
        return players_data
    
    games = series_state.get("games", [])
    
    for game in games:
        game_id = game.get("id", "N/A")
        game_number = game.get("sequenceNumber", 0)
        game_teams = game.get("teams", [])
        
        for team in game_teams:
            team_name = team.get("name", "N/A")
            team_id = team.get("id", "N/A")
            players = team.get("players", [])
            
            for player in players:
                # Extract position data
                position = player.get("position", {})
                position_x = position.get("x", "N/A") if position else "N/A"
                position_y = position.get("y", "N/A") if position else "N/A"
                
                player_record = {
                    "series_id": series_id,
                    "game_id": game_id,
                    "game_number": game_number,
                    "team_name": team_name,
                    "team_id": team_id,
                    "player_id": player.get("id", "N/A"),
                    "player_name": player.get("name", "N/A"),
                    "kills": player.get("kills", 0),
                    "deaths": player.get("deaths", 0),
                    "net_worth": player.get("netWorth", "N/A"),
                    "money": player.get("money", "N/A"),
                    "position_x": position_x,
                    "position_y": position_y,
                    "tournament": series_metadata.get("tournament", "N/A"),
                    "game_title": series_metadata.get("title", "N/A")
                }
                
                players_data.append(player_record)
    
    return players_data


def save_games_csv(games_data, base_filename):
    """Save games detail data to CSV"""
    filename = build_filename(base_filename, suffix="_games")
    
    fieldnames = [
        "series_id",
        "game_id",
        "game_number",
        "game_started",
        "game_started_at",
        "game_finished",
        "game_finished_at",
        "map_id",
        "map_name",
        "team_1_name",
        "team_1_id",
        "team_1_side",
        "team_1_score",
        "team_1_won",
        "team_2_name",
        "team_2_id",
        "team_2_side",
        "team_2_score",
        "team_2_won",
        "tournament",
        "game_title"
    ]
    
    return save_csv_file(games_data, filename, fieldnames, data_type="games")


def get_team_metadata(team_id):
    """
    Get team metadata from Central Data Feed API
    Returns dict with team info or None if not found
    """
    query = """
    query GetTeam($teamId: ID!) {
        team(id: $teamId) {
            id
            name
            logoUrl
        }
    }
    """
    
    try:
        response = requests.post(
            CENTRAL_DATA_GRAPHQL_ENDPOINT,
            headers={
                "x-api-key": GRID_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "query": query,
                "variables": {"teamId": str(team_id)}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "errors" not in data:
                team = data.get("data", {}).get("team", {})
                if team:
                    return {
                        "team_id": team.get("id"),
                        "team_name": team.get("name", "N/A"),
                        "team_logo_url": team.get("logoUrl", "N/A")
                    }
        return None
    except Exception as e:
        return None


def create_team_summaries(all_games_data, summaries):
    """
    Create team summary data by collecting unique teams
    Returns list of team summary dicts
    """
    teams_dict = {}
    
    # Collect unique teams from games data
    for game in all_games_data:
        for team_num in [1, 2]:
            team_id = game.get(f"team_{team_num}_id")
            team_name = game.get(f"team_{team_num}_name")
            
            if team_id and team_id != "N/A" and team_id not in teams_dict:
                teams_dict[team_id] = {
                    "team_id": team_id,
                    "team_name": team_name,
                    "game_title": game.get("game_title", "N/A"),
                    "team_logo_url": "N/A",
                    "series_count": 0,
                    "games_played": 0,
                    "games_won": 0,
                    "games_lost": 0
                }
    
    # Also collect from summaries (in case some series have no games)
    for summary in summaries:
        for team_num in [1, 2]:
            team_id = summary.get(f"team_{team_num}_id")
            team_name = summary.get(f"team_{team_num}_name")
            
            if team_id and team_id != "N/A" and team_id not in teams_dict:
                teams_dict[team_id] = {
                    "team_id": team_id,
                    "team_name": team_name,
                    "game_title": summary.get("game_title", "N/A"),
                    "team_logo_url": "N/A",
                    "series_count": 0,
                    "games_played": 0,
                    "games_won": 0,
                    "games_lost": 0
                }
    
    # Aggregate stats from games
    for game in all_games_data:
        for team_num in [1, 2]:
            team_id = game.get(f"team_{team_num}_id")
            if team_id and team_id in teams_dict:
                teams_dict[team_id]["games_played"] += 1
                if game.get(f"team_{team_num}_won") == "Yes":
                    teams_dict[team_id]["games_won"] += 1
                else:
                    teams_dict[team_id]["games_lost"] += 1
    
    # Count series from summaries
    for summary in summaries:
        for team_num in [1, 2]:
            team_id = summary.get(f"team_{team_num}_id")
            if team_id and team_id in teams_dict:
                teams_dict[team_id]["series_count"] += 1
    
    # Get metadata from Central Data Feed for each team
    logging.info(f"   Fetching team metadata from Central Data Feed...")
    for team_id in teams_dict.keys():
        metadata = get_team_metadata(team_id)
        if metadata:
            teams_dict[team_id]["team_logo_url"] = metadata.get("team_logo_url", "N/A")
        time.sleep(0.1)  # Rate limiting
    
    return list(teams_dict.values())


def create_player_summaries(all_players_data):
    """
    Create player summary data by aggregating stats
    Returns list of player summary dicts
    """
    players_dict = {}
    
    # Aggregate player stats
    for player_record in all_players_data:
        player_id = player_record.get("player_id")
        
        if player_id and player_id != "N/A":
            if player_id not in players_dict:
                players_dict[player_id] = {
                    "player_id": player_id,
                    "player_name": player_record.get("player_name", "N/A"),
                    "team_id": player_record.get("team_id", "N/A"),
                    "team_name": player_record.get("team_name", "N/A"),
                    "game_title": player_record.get("game_title", "N/A"),
                    "games_played": 0,
                    "total_kills": 0,
                    "total_deaths": 0,
                    "total_net_worth": 0,
                    "total_money": 0,
                    "avg_kills": 0.0,
                    "avg_deaths": 0.0,
                    "avg_net_worth": 0.0,
                    "avg_money": 0.0,
                    "kd_ratio": 0.0
                }
            
            # Aggregate stats
            players_dict[player_id]["games_played"] += 1
            players_dict[player_id]["total_kills"] += player_record.get("kills", 0)
            players_dict[player_id]["total_deaths"] += player_record.get("deaths", 0)
            
            # Add economic stats (handle N/A values)
            net_worth = player_record.get("net_worth", 0)
            money = player_record.get("money", 0)
            if net_worth != "N/A" and isinstance(net_worth, (int, float)):
                players_dict[player_id]["total_net_worth"] += net_worth
            if money != "N/A" and isinstance(money, (int, float)):
                players_dict[player_id]["total_money"] += money
    
    # Calculate averages and K/D ratio
    for player_id, player_data in players_dict.items():
        games = player_data["games_played"]
        if games > 0:
            player_data["avg_kills"] = round(player_data["total_kills"] / games, 2)
            player_data["avg_deaths"] = round(player_data["total_deaths"] / games, 2)
            player_data["avg_net_worth"] = round(player_data["total_net_worth"] / games, 2)
            player_data["avg_money"] = round(player_data["total_money"] / games, 2)
            
            if player_data["total_deaths"] > 0:
                player_data["kd_ratio"] = round(player_data["total_kills"] / player_data["total_deaths"], 2)
            else:
                player_data["kd_ratio"] = player_data["total_kills"]  # Perfect K/D
    
    return list(players_dict.values())


def save_team_summary_csv(team_data, base_filename):
    """Save team summary data to CSV"""
    filename = build_filename(base_filename, suffix="_teams")
    
    fieldnames = [
        "team_id",
        "team_name",
        "team_logo_url",
        "game_title",
        "series_count",
        "games_played",
        "games_won",
        "games_lost"
    ]
    
    return save_csv_file(team_data, filename, fieldnames, data_type="teams")


def save_player_summary_csv(player_data, base_filename):
    """Save player summary data to CSV"""
    filename = build_filename(base_filename, suffix="_player_summary")
    
    fieldnames = [
        "player_id",
        "player_name",
        "team_id",
        "team_name",
        "game_title",
        "games_played",
        "total_kills",
        "total_deaths",
        "avg_kills",
        "avg_deaths",
        "kd_ratio",
        "total_net_worth",
        "total_money",
        "avg_net_worth",
        "avg_money"
    ]
    
    return save_csv_file(player_data, filename, fieldnames, data_type="player summaries")


def save_players_csv(players_data, base_filename):
    """Save players detail data to CSV"""
    filename = build_filename(base_filename, suffix="_players")
    
    fieldnames = [
        "series_id",
        "game_id",
        "game_number",
        "team_name",
        "team_id",
        "player_id",
        "player_name",
        "kills",
        "deaths",
        "net_worth",
        "money",
        "position_x",
        "position_y",
        "tournament",
        "game_title"
    ]
    
    return save_csv_file(players_data, filename, fieldnames, data_type="player records")


def save_to_csv(summaries, base_filename):
    """Save summaries to CSV file"""
    filename = build_filename(base_filename)
    
    # Define CSV columns (metadata + series state data + team scores)
    fieldnames = [
        "series_id",
        "game_title",
        "tournament",
        "tournament_id",
        "series_type",
        "start_time",
        "team_1_name",
        "team_1_id",
        "team_1_score",
        "team_2_name",
        "team_2_id",
        "team_2_score",
        "series_started",
        "series_finished",
        "series_format",
        "team_1_won",
        "team_2_won",
        "winner",
        "games_played"
    ]
    
    return save_csv_file(summaries, filename, fieldnames, data_type="series")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='GRID Game Series Data Puller - Pull esports data from GRID API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pull 50 CS2 series (auto-queries with smart mode)
  uv run grid_data_pull.py --game cs2
  
  # Pull 100 Dota 2 series with summary detail only
  uv run grid_data_pull.py --game dota2 --series 100 --detail summary
  
  # Pull specific series IDs (bypasses auto-query)
  uv run grid_data_pull.py --game cs2 --ids 123,456,789
  
  # Fast mode: get most recent series (may have no data)
  uv run grid_data_pull.py --game csgo --mode recent --series 20
  
  # Smart mode: ensure all series have data (default, slower)
  uv run grid_data_pull.py --game dota2 --mode smart --series 50
  
  # Increase check limit if not finding enough series
  uv run grid_data_pull.py --game dota2 --series 50 --max-check 3000
  
  # Verbose mode (DEBUG level)
  uv run grid_data_pull.py --game cs2 --verbose
  
  # Quiet mode (warnings/errors only)
  uv run grid_data_pull.py --game dota2 --quiet
  
  # Save logs to file
  uv run grid_data_pull.py --game cs2 --log-file grid_pull.log

Query Modes:
  --mode smart  = Finds series with completed match data (100% have data, slower)
  --mode recent = Gets most recent series (fast, but may be future/scheduled)
  
  If --ids is provided, --mode is ignored (specific IDs are used directly).

Logging Levels:
  Default     = INFO level (normal operation logs)
  --verbose   = DEBUG level (detailed API responses, errors)
  --quiet     = WARNING level (only warnings and errors)
  --log-file  = Also write logs to specified file
        """
    )
    
    parser.add_argument(
        '--game',
        type=str,
        choices=['dota2', 'csgo', 'cs2'],
        default=None,
        help='Game to pull data for (dota2, csgo, or cs2). Default: use config value'
    )
    
    parser.add_argument(
        '--series',
        type=int,
        default=None,
        help='Number of series to pull. Default: use config value (50)'
    )
    
    parser.add_argument(
        '--detail',
        type=str,
        choices=['summary', 'games', 'full'],
        default=None,
        help='Detail level: summary (main CSV only), games (main + games), full (all CSVs). Default: use config value (full)'
    )
    
    parser.add_argument(
        '--ids',
        type=str,
        default=None,
        help='(Optional) Comma-separated specific series IDs to query (e.g., "2,123,456"). If not provided, auto-queries series based on --mode.'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['smart', 'recent'],
        default=None,
        help='''Query mode for auto-querying series (ignored if --ids is provided):
  smart  = Find most recent series WITH completed match data (slower, 100%% success rate, checks up to --max-check series)
  recent = Get most recent series regardless of status (faster, may include future/scheduled matches with no data yet)
Default: smart'''
    )
    
    parser.add_argument(
        '--max-check',
        type=int,
        default=None,
        help='(Smart mode only) Maximum number of series to check before stopping. Increase if not finding enough completed series. Default: 2000'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level). Shows detailed API responses and errors.'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode (WARNING level only). Shows only warnings and errors.'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default=None,
        help='Optional log file path. If provided, logs will be written to this file in addition to console.'
    )
    
    return parser.parse_args()


def main():
    """Main execution function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging based on command-line flags
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    setup_logging(log_level=log_level, log_file=args.log_file)
    
    # Override CONFIG with command line arguments if provided
    if args.game:
        CONFIG["game"] = args.game
    
    if args.series:
        CONFIG["num_series"] = args.series
    
    if args.detail:
        CONFIG["detail_level"] = args.detail
    
    if args.ids:
        # Parse comma-separated IDs
        CONFIG["specific_series_ids"] = [id.strip() for id in args.ids.split(',')]
    
    if args.mode:
        CONFIG["query_mode"] = args.mode
    
    if args.max_check:
        CONFIG["max_series_to_check"] = args.max_check
    
    game_name = GAME_CONFIG[CONFIG["game"]]["name"]
    output_dir = CONFIG.get("output_directory", ".")
    
    print("\n" + "=" * 100)
    print(f"🎮 GRID {game_name} Series Summary Data Puller")
    print("=" * 100)
    print()
    
    if not GRID_API_KEY:
        logging.info("❌ Error: GRID_DATA_API_KEY not found in .env file")
        return
    
    logging.info("✅ API Key loaded")
    logging.info(f"📊 Selected Game: {game_name}")
    logging.info(f"📊 Using titleId: {GAME_CONFIG[CONFIG['game']]['title_id']}")
    logging.info(f"📁 Output directory: {output_dir}/")
    
    print()
    
    # Step 1: Get series metadata from Central Data Feed
    logging.info(f"📊 STEP 1: Getting {game_name} Series Metadata")
    logging.info("-" * 100)
    
    if CONFIG["specific_series_ids"]:
        # Use specific series IDs provided by user
        logging.info(f"🎯 Using {len(CONFIG['specific_series_ids'])} specific series IDs provided...")
        series_list = []
        for series_id in CONFIG["specific_series_ids"]:
            series_list.append({
                "id": series_id,
                "title": f"{game_name}",
                "tournament": "Manual Selection",
                "tournament_id": "N/A",
                "type": "ESPORTS",
                "start_time": "N/A",
                "team_1_name": "N/A",
                "team_1_id": "N/A",
                "team_2_name": "N/A",
                "team_2_id": "N/A"
            })
    else:
        # Auto-query based on mode
        if CONFIG["query_mode"] == "smart":
            # Smart mode: Find series with completed data
            logging.info(f"📊 Query Mode: SMART (finding series with completed data)")
            series_list = get_completed_series_with_state(
                CONFIG["game"], 
                num_series=CONFIG["num_series"],
                max_to_check=CONFIG["max_series_to_check"]
            )
        else:
            # Recent mode: Get most recent series (may not have data)
            logging.info(f"📊 Query Mode: RECENT (getting most recent series)")
            series_list = get_series_ids(CONFIG["game"], num_series=CONFIG["num_series"])
    
    if not series_list:
        logging.info("❌ No series found. Exiting.")
        return
    
    print()
    logging.info(f"✅ Retrieved {len(series_list)} series")
    print()
    
    # Step 2: Get series state data and create summaries
    logging.info("📊 STEP 2: Getting Series State Data (Teams, Scores, Winners)")
    logging.info("-" * 100)
    logging.info("🔍 Using correct GraphQL endpoint for Series State API")
    
    summaries = []
    all_games_data = []
    all_players_data = []
    series_with_state = 0
    series_without_state = 0
    
    detail_level = CONFIG.get("detail_level", "summary")
    
    for i, series in enumerate(series_list, 1):
        series_id = series["id"]
        
        # Try to get series state data
        series_state = get_series_state(series_id)
        
        if series_state and series_state.get("valid"):
            series_with_state += 1
            logging.info(f"   [{i}/{len(series_list)}] Series {series_id}... ✅ Got state data")
        else:
            series_without_state += 1
            logging.info(f"   [{i}/{len(series_list)}] Series {series_id}... ⚠️  No state data")
        
        # Create summary with or without state data
        summary = create_summary(series, series_state)
        summaries.append(summary)
        
        # Extract games and players data if needed
        if detail_level in ["games", "full"] and series_state:
            games_data = extract_games_data(series_id, series_state, series)
            all_games_data.extend(games_data)
        
        if detail_level == "full" and series_state:
            players_data = extract_players_data(series_id, series_state, series)
            all_players_data.extend(players_data)
        
        # Add small delay to avoid rate limiting
        if i < len(series_list):
            time.sleep(0.2)
    
    print()
    logging.info(f"✅ Processed {len(summaries)} series")
    logging.info(f"   Series with state data: {series_with_state}")
    logging.info(f"   Series without state data: {series_without_state}")
    print()
    
    # Step 3: Display summary statistics
    logging.info("📊 STEP 3: Summary Statistics")
    logging.info("-" * 100)
    
    # Count by tournament
    tournament_counts = {}
    for s in summaries:
        tournament = s["tournament"]
        tournament_counts[tournament] = tournament_counts.get(tournament, 0) + 1
    
    logging.info(f"Total series: {len(summaries)}")
    logging.info(f"Unique tournaments: {len(tournament_counts)}")
    logging.info(f"Top 5 tournaments:")
    for tournament, count in sorted(tournament_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        logging.info(f"  - {tournament}: {count} series")
    
    # Show data collection stats
    if detail_level in ["games", "full"]:
        logging.info(f"Games collected: {len(all_games_data)}")
        if series_with_state < len(summaries):
            logging.info(f"⚠️  Note: {len(summaries) - series_with_state} series have no games data")
    if detail_level == "full":
        logging.info(f"Player records collected: {len(all_players_data)}")
        if series_with_state < len(summaries):
            logging.info(f"⚠️  Note: {len(summaries) - series_with_state} series have no player data")
    print()
    
    # Step 4: Save to CSV
    logging.info("📊 STEP 4: Saving to CSV")
    logging.info("-" * 100)
    logging.info(f"📊 Detail Level: {detail_level.upper()}")
    print()
    
    # Save main summary CSV
    csv_file = save_to_csv(summaries, get_base_filename())
    
    saved_files = []
    if csv_file:
        saved_files.append(csv_file)
    
    # Save games CSV if detail level includes games
    if detail_level in ["games", "full"] and all_games_data:
        games_file = save_games_csv(all_games_data, get_base_filename())
        if games_file:
            saved_files.append(games_file)
    
    # Save players CSV if detail level is full
    if detail_level == "full" and all_players_data:
        players_file = save_players_csv(all_players_data, get_base_filename())
        if players_file:
            saved_files.append(players_file)
    
    # Generate and save team summary
    if detail_level in ["games", "full"] and all_games_data:
        print()
        logging.info("   Creating team summary...")
        team_summaries = create_team_summaries(all_games_data, summaries)
        if team_summaries:
            team_file = save_team_summary_csv(team_summaries, get_base_filename())
            if team_file:
                saved_files.append(team_file)
    
    # Generate and save player summary
    if detail_level == "full" and all_players_data:
        print()
        logging.info("   Creating player summary...")
        player_summaries = create_player_summaries(all_players_data)
        if player_summaries:
            player_summary_file = save_player_summary_csv(player_summaries, get_base_filename())
            if player_summary_file:
                saved_files.append(player_summary_file)
    
    if saved_files:
        print()
        logging.info("✅ Data pull complete!")
        logging.info(f"📄 Generated {len(saved_files)} file(s):")
        for file in saved_files:
            logging.info(f"   - {file}")
        
        # Data integrity note
        if detail_level in ["games", "full"] and series_without_state > 0:
            print()
            logging.info("⚠️  DATA INTEGRITY NOTE:")
            logging.info(f"   {series_without_state} series in summary CSV have no games/players data")
            logging.info(f"   Filter by games_played > 0 before joining CSVs")
            logging.info(f"   See ENHANCED_DATA_GUIDE.md for details")
    
    print()
    print("=" * 100)
    print()


if __name__ == "__main__":
    main()
