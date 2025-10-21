"""NFL Box Score Scraper for Raw Statistics - Database Version"""

import argparse
import sys
from typing import Dict, List, Optional
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from utils import clean_player_name
import time
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
    NoSuchElementException
)

# Database imports
from database.database_manager import DatabaseManager
from database.database_models import BoxScore, Game
from datetime import datetime

class FootballDBScraper:
    """Scraper for FootballDB box scores"""
    
    def __init__(self, week: int):
        self.week = week
        self.base_url = "https://www.footballdb.com"
        self.driver = None
        self.db_manager = DatabaseManager()
        
        # Define expected columns for each stat type
        self.stat_columns = {
            'passing': ["player", "pass_Yds", "pass_TD", "pass_INT"],
            'rushing': ["player", "rush_Yds", "rush_TD"],
            'receiving': ["player", "rec_Rec", "rec_Yds", "rec_TD"]
        }
        
    def setup_driver(self) -> webdriver.Firefox:
        """Initialize Selenium WebDriver"""
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(10)  # Reduce from 120 to improve performance
        self.wait = WebDriverWait(self.driver, 10)
        return self.driver
        
    def get_game_links(self) -> List[str]:
        """Get all game URLs for the specified week"""
        try:
            print(f"Navigating to {self.base_url}/games/index.html")
            self.driver.get(f"{self.base_url}/games/index.html")
            
            # Wait for content to load with multiple possible selectors
            selectors_to_try = [
                (By.CLASS_NAME, "statistics"),
                (By.TAG_NAME, "table"),
                (By.CLASS_NAME, "games"),
                (By.ID, "games")
            ]
            
            content_found = False
            for selector_type, selector_value in selectors_to_try:
                try:
                    print(f"Trying to find element with {selector_type}: {selector_value}")
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    content_found = True
                    print(f"Found content with {selector_type}: {selector_value}")
                    break
                except TimeoutException:
                    print(f"Timeout waiting for {selector_type}: {selector_value}")
                    continue
            
            if not content_found:
                print("Could not find any expected content, proceeding anyway...")
            
            # Add delay to ensure page is fully loaded
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            print(f"Page title: {soup.title.string if soup.title else 'No title found'}")
            
            # Try multiple approaches to find games table
            games_table = None
            
            # Approach 1: Look for statistics class
            tables = soup.find_all('table', class_='statistics')
            if tables and len(tables) >= self.week:
                games_table = tables[self.week - 1]
                print(f"Found games table using statistics class (week {self.week})")
            
            # Approach 2: Look for any table with game links
            if not games_table:
                all_tables = soup.find_all('table')
                for i, table in enumerate(all_tables):
                    links = table.find_all('a', href=True)
                    if any('boxscore' in link.get('href', '') for link in links):
                        if i == self.week - 1:  # Assuming tables are in week order
                            games_table = table
                            print(f"Found games table at index {i}")
                            break
            
            # Approach 3: Look for any links containing boxscore
            if not games_table:
                all_links = soup.find_all('a', href=True)
                boxscore_links = [link for link in all_links if 'boxscore' in link.get('href', '')]
                if boxscore_links:
                    print(f"Found {len(boxscore_links)} boxscore links directly")
                    return [link.get('href') for link in boxscore_links]
            
            if not games_table:
                print("Could not find games table, trying to extract links from page...")
                # Last resort: look for any boxscore links on the page
                all_links = soup.find_all('a', href=True)
                boxscore_links = [link.get('href') for link in all_links if 'boxscore' in link.get('href', '')]
                return boxscore_links
            
            # Extract links from the found table
            links = []
            for row in games_table.find_all('tr'):
                link_elem = row.find("a")
                if link_elem and link_elem.get('href'):
                    links.append(link_elem.get('href'))
            
            print(f"Found {len(links)} game links")
            return links
            
        except Exception as e:
            print(f"Error getting game links: {e}")
            print("Trying alternative approach...")
            
            # Alternative: try to construct URLs manually for common patterns
            try:
                # Try to get the current year from the URL or page
                current_year = "2025"  # Default to 2024
                alternative_links = []
                
                # Common game patterns for week 4
                if self.week == 4:
                    # These are example URLs - we'd need to get the actual game URLs
                    print("Attempting to construct alternative URLs for Week 4...")
                    # This is a fallback - in practice we'd need the actual game URLs
                
                return alternative_links
            except Exception as e2:
                print(f"Alternative approach also failed: {e2}")
                return []
            
    def extract_game_teams(self, stats_div) -> Dict[str, str]:
        """Extract team names from the game page"""
        teams = {'visitor': 'Unknown', 'home': 'Unknown'}
        
        try:
            # Look for statsvisitor and statshome divs to get team names
            visitor_div = stats_div.find('div', class_='statsvisitor')
            home_div = stats_div.find('div', class_='statshome')
            
            if visitor_div:
                # Get first table in visitor div to extract team name
                visitor_table = visitor_div.find('table')
                if visitor_table:
                    visitor_team = self.extract_team_from_table(visitor_table)
                    if visitor_team:
                        teams['visitor'] = visitor_team
            
            if home_div:
                # Get first table in home div to extract team name
                home_table = home_div.find('table')
                if home_table:
                    home_team = self.extract_team_from_table(home_table)
                    if home_team:
                        teams['home'] = home_team
            
            return teams
            
        except Exception as e:
            print(f"Error extracting game teams: {e}")
            return teams
    
    def extract_team_from_table(self, table) -> str:
        """Extract team name from a single table"""
        try:
            header = table.find("thead")
            if header:
                first_th = header.find("th")
                if first_th:
                    # Look for team name in the span elements - prefer desktop version (full name)
                    team_span = first_th.find("span", class_="d-none d-xl-inline")
                    if team_span:
                        return team_span.text.strip()
                    else:
                        # Try mobile version as fallback
                        team_span_mobile = first_th.find("span", class_="d-inline d-xl-none")
                        if team_span_mobile:
                            return team_span_mobile.text.strip()
                        else:
                            # Fallback to the full text if no span found
                            return first_th.text.strip()
        except Exception as e:
            print(f"Error extracting team from table: {e}")
        return "Unknown"

    def parse_stats_table(self, table, stat_type: str, game_teams: Dict[str, str] = None) -> pd.DataFrame:
        """Parse a single stats table into a DataFrame"""
        try:
            header = table.find("thead")
            body = table.find("tbody")
            
            if not header or not body:
                print(f"No header or body found for {stat_type} table")
                return pd.DataFrame(columns=self.stat_columns[stat_type])
            
            # Get raw column names, but clean the first column to avoid duplicated team names
            columns = []
            for th in header.find_all("th"):
                col_text = th.text.strip()
                # If this is the first column (team name), clean it
                if len(columns) == 0:
                    # Extract just the team name from the first column
                    if game_teams:
                        # Use the team name we already extracted
                        columns.append('Team')
                    else:
                        # Fallback: try to clean the duplicated name
                        if len(col_text) > 15 and any(team_word in col_text.lower() for team_word in ['cowboys', 'eagles', 'patriots', 'packers', 'steelers', 'ravens', 'bills', 'chiefs', 'bengals', 'browns', 'broncos', 'texans', 'colts', 'jaguars', 'titans', 'raiders', 'chargers', 'rams', 'dolphins', 'jets', 'saints', 'buccaneers', 'cardinals', 'falcons', 'panthers', 'bears', 'lions', 'vikings', 'giants', 'commanders', 'seahawks', '49ers']):
                            # Split on the team name and take the first part
                            for team_word in ['Cowboys', 'Eagles', 'Patriots', 'Packers', 'Steelers', 'Ravens', 'Bills', 'Chiefs', 'Bengals', 'Browns', 'Broncos', 'Texans', 'Colts', 'Jaguars', 'Titans', 'Raiders', 'Chargers', 'Rams', 'Dolphins', 'Jets', 'Saints', 'Buccaneers', 'Cardinals', 'Falcons', 'Panthers', 'Bears', 'Lions', 'Vikings', 'Giants', 'Commanders', 'Seahawks', '49ers']:
                                if team_word in col_text:
                                    parts = col_text.split(team_word)
                                    if len(parts) > 1:
                                        columns.append(parts[0] + team_word)
                                        break
                                    else:
                                        columns.append(col_text)
                                        break
                            else:
                                columns.append(col_text)
                        else:
                            columns.append(col_text)
                else:
                    columns.append(col_text)
            
            # Determine which team this table represents
            team_name = "Unknown"
            if game_teams:
                # Check if this table is in a visitor or home div
                parent_div = table.find_parent('div')
                if parent_div:
                    div_classes = parent_div.get('class', [])
                    if 'statsvisitor' in div_classes:
                        team_name = game_teams.get('visitor', 'Unknown')
                    elif 'statshome' in div_classes:
                        team_name = game_teams.get('home', 'Unknown')
                    else:
                        # Fallback: extract from table header
                        team_name = self.extract_team_from_table(table)
                else:
                    # Fallback: extract from table header
                    team_name = self.extract_team_from_table(table)
            else:
                # Fallback: extract from table header
                team_name = self.extract_team_from_table(table)
            
            # Define column mappings for each stat type based on actual HTML
            column_maps = {
                'passing': {
                    'Yds': 'pass_Yds', 
                    'TD': 'pass_TD', 
                    'Int': 'pass_INT',
                    'Att': 'pass_Att',
                    'Cmp': 'pass_Cmp'
                },
                'rushing': {
                    'Yds': 'rush_Yds', 
                    'TD': 'rush_TD',
                    'Att': 'rush_Att'
                },
                'receiving': {
                    'Rec': 'rec_Rec', 
                    'Yds': 'rec_Yds', 
                    'TD': 'rec_TD',
                    'Tar': 'rec_Tar'
                }
            }
            
            rows = []
            for row in body.find_all("tr"):
                # Skip TOTAL rows
                if 'TOTAL' in row.get_text():
                    continue
                    
                values = [td.text.strip() for td in row.find_all("td")]
                if len(values) >= len(columns):
                    row_dict = dict(zip(columns, values))
                    
                    # Extract player name from the first cell by looking at the actual HTML structure
                    first_cell = row.find("td")
                    player_name = "Unknown"
                    if first_cell:
                        # Look for player name in span elements - prefer desktop version (full name)
                        name_span = first_cell.find("span", class_="d-none d-xl-inline")
                        if name_span:
                            player_name = name_span.text.strip()
                        else:
                            # Try mobile version as fallback
                            name_span_mobile = first_cell.find("span", class_="d-inline d-xl-none")
                            if name_span_mobile:
                                player_name = name_span_mobile.text.strip()
                            else:
                                # Fallback to the full text if no span found
                                full_text = first_cell.text.strip()
                                player_name = full_text
                    
                    # Clean player name
                    if player_name:
                        # Remove any HTML tags that might be in the text
                        player_name = player_name.replace('\xa0', ' ')  # Replace non-breaking spaces
                        player_name = clean_player_name(player_name)
                    
                    if not player_name or player_name == 'TOTAL':
                        continue
                    
                    # Map column names to our expected format
                    mapped_dict = {'player': player_name, 'team': team_name}
                    for old_col, new_col in column_maps[stat_type].items():
                        # Look for columns that contain the old_col text
                        for col in columns:
                            if old_col in col:
                                value = row_dict.get(col, '0')
                                # Clean the value (remove 't' from TD values, etc.)
                                if value.endswith('t'):
                                    value = value[:-1]
                                mapped_dict[new_col] = value
                                break
                    
                    rows.append(mapped_dict)
            
            df = pd.DataFrame(rows)
            return df
            
        except Exception as e:
            print(f"Error parsing {stat_type} stats table: {e}")
            return pd.DataFrame(columns=self.stat_columns[stat_type])
            
    def process_game(self, game_url: str) -> Dict[str, pd.DataFrame]:
        """Process a single game's box score"""
        try:
            full_url = f"{self.base_url}{game_url}" if not game_url.startswith('http') else game_url
            print(f"Processing game: {full_url}")
            
            self.driver.get(full_url)
            
            # Wait longer for the page to fully load
            print("Waiting for page to load...")
            time.sleep(5)  # Initial wait
            
            # Try multiple approaches to find stats
            stats_div = None
            
            # Approach 1: Look for mobToggle_stats (the actual ID from the HTML)
            try:
                print("Waiting for mobToggle_stats element...")
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "mobToggle_stats"))
                )
                # Additional wait after finding the element
                time.sleep(3)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                stats_div = soup.find('div', {"id": "mobToggle_stats"})
                print("Found stats using mobToggle_stats ID")
                
                # Debug: Check what's actually in the stats div
                if stats_div:
                    print(f"Stats div found with {len(stats_div.find_all('h2'))} h2 headers")
                    print(f"Stats div found with {len(stats_div.find_all('table'))} tables")
                    print(f"Stats div found with {len(stats_div.find_all('div', class_='statsvisitor'))} statsvisitor divs")
                    print(f"Stats div found with {len(stats_div.find_all('div', class_='statshome'))} statshome divs")
                else:
                    print("Stats div not found in soup")
                    
            except TimeoutException:
                print("mobToggle_stats not found, trying alternative approaches...")
            
            # Approach 2: Look for divBox_stats (old approach)
            if not stats_div:
                try:
                    print("Waiting for divBox_stats element...")
                    self.wait.until(
                        EC.presence_of_element_located((By.ID, "divBox_stats"))
                    )
                    time.sleep(3)
                    soup = BeautifulSoup(self.driver.page_source, "html.parser")
                    stats_div = soup.find('div', {"id": "divBox_stats"})
                    print("Found stats using divBox_stats ID")
                except TimeoutException:
                    print("divBox_stats not found, trying alternative approaches...")
            
            # Approach 3: Look for any div with stats
            if not stats_div:
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                stats_divs = soup.find_all('div', class_=lambda x: x and 'stats' in x.lower())
                if stats_divs:
                    stats_div = stats_divs[0]
                    print("Found stats using class containing 'stats'")
            
            # Approach 4: Look for tables directly
            if not stats_div:
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                tables = soup.find_all("table")
                if tables:
                    print(f"Found {len(tables)} tables directly on page")
                    # Use the page itself as the stats container
                    stats_div = soup
            
            if not stats_div:
                print(f"No stats found for game {game_url}")
                # Debug: Let's see what's actually on the page
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                print(f"Page has {len(soup.find_all('div'))} divs")
                print(f"Page has {len(soup.find_all('table'))} tables")
                print(f"Page has {len(soup.find_all('h2'))} h2 headers")
                return {}
            
            # Extract team names from the game page first
            game_teams = self.extract_game_teams(stats_div)
            
            # Process stats based on the actual HTML structure
            stats = {
                'passing': pd.DataFrame(columns=self.stat_columns['passing']),
                'rushing': pd.DataFrame(columns=self.stat_columns['rushing']),
                'receiving': pd.DataFrame(columns=self.stat_columns['receiving'])
            }
            
            # Look for h2 headers to identify sections
            h2_headers = stats_div.find_all('h2')
            
            # Process each section based on h2 headers
            for h2 in h2_headers:
                section_name = h2.text.strip().lower()
                
                # Find all tables that follow this h2 until the next h2
                # Look for tables within statsvisitor and statshome divs
                section_tables = []
                next_element = h2.find_next_sibling()
                
                while next_element and next_element.name != 'h2':
                    if next_element.name == 'div':
                        div_classes = next_element.get('class', [])
                        if 'statsvisitor' in div_classes or 'statshome' in div_classes:
                            # Found a stats div, look for tables within it
                            tables_in_div = next_element.find_all('table')
                            section_tables.extend(tables_in_div)
                    elif next_element.name == 'table':
                        # Direct table (fallback)
                        section_tables.append(next_element)
                    
                    next_element = next_element.find_next_sibling()
                
                # Process tables based on section type
                if 'pass' in section_name:
                    for table in section_tables:
                        table_stats = self.parse_stats_table(table, 'passing', game_teams)
                        if not table_stats.empty:
                            stats['passing'] = pd.concat([stats['passing'], table_stats], ignore_index=True)
                elif 'rush' in section_name:
                    for table in section_tables:
                        table_stats = self.parse_stats_table(table, 'rushing', game_teams)
                        if not table_stats.empty:
                            stats['rushing'] = pd.concat([stats['rushing'], table_stats], ignore_index=True)
                elif 'receiv' in section_name:
                    for table in section_tables:
                        table_stats = self.parse_stats_table(table, 'receiving', game_teams)
                        if not table_stats.empty:
                            stats['receiving'] = pd.concat([stats['receiving'], table_stats], ignore_index=True)
            
            # If no h2 headers found, try the old approach with table indices
            if not h2_headers:
                print("No h2 headers found, trying table index approach...")
                tables = stats_div.find_all("table")
                print(f"Found {len(tables)} tables in stats div")
                
                if len(tables) >= 6:
                    # Original approach with 6 tables
                    stats = {
                        'passing': pd.concat([self.parse_stats_table(t, 'passing', game_teams) for t in tables[:2]]),
                        'rushing': pd.concat([self.parse_stats_table(t, 'rushing', game_teams) for t in tables[2:4]]),
                        'receiving': pd.concat([self.parse_stats_table(t, 'receiving', game_teams) for t in tables[4:6]])
                    }
                elif len(tables) > 0:
                    # Try to process whatever tables we have
                    for i, table in enumerate(tables):
                        table_text = table.get_text().lower()
                        if 'pass' in table_text or 'comp' in table_text or 'att' in table_text:
                            table_stats = self.parse_stats_table(table, 'passing', game_teams)
                            if not table_stats.empty:
                                stats['passing'] = pd.concat([stats['passing'], table_stats], ignore_index=True)
                        elif 'rush' in table_text or 'car' in table_text:
                            table_stats = self.parse_stats_table(table, 'rushing', game_teams)
                            if not table_stats.empty:
                                stats['rushing'] = pd.concat([stats['rushing'], table_stats], ignore_index=True)
                        elif 'rec' in table_text or 'catch' in table_text or 'target' in table_text:
                            table_stats = self.parse_stats_table(table, 'receiving', game_teams)
                            if not table_stats.empty:
                                stats['receiving'] = pd.concat([stats['receiving'], table_stats], ignore_index=True)
            
            return stats
            
        except Exception as e:
            print(f"Error processing game {game_url}: {e}")
            return {}
            
    def process_all_games(self) -> pd.DataFrame:
        """Process all games and combine stats with retry logic"""
        try:
            game_links = self.get_game_links()
            print(f"Found {len(game_links)} games to process")
            
            if not game_links:
                print("No game links found!")
                return pd.DataFrame()
            
            all_stats = []
            for i, link in enumerate(game_links, 1):
                print(f"\nProcessing game {i}/{len(game_links)}")
                
                # Try up to 3 times to process each game
                for attempt in range(3):
                    try:
                        if attempt > 0:
                            print(f"Retry attempt {attempt + 1} for game {link}")
                            
                        game_stats = self.process_game(link)
                        if game_stats:
                            all_stats.append(game_stats)
                            break
                        
                        # If no stats but no error, just move on
                        if attempt == 0:
                            print(f"No stats found for game {link}, skipping...")
                            break
                            
                    except Exception as e:
                        print(f"Error on attempt {attempt + 1}: {e}")
                        if attempt == 2:  # Last attempt
                            print(f"Failed to process game {link} after 3 attempts, skipping...")
                        else:
                            print("Waiting 5 seconds before retry...")
                            time.sleep(5)
                            # Refresh the page before retry
                            try:
                                self.driver.refresh()
                            except:
                                pass
                
            if not all_stats:
                print("No valid games processed!")
                return pd.DataFrame()
                    
            # Combine all game stats
            print("\nCombining stats from all games...")
            combined_stats = {
                'passing': pd.concat([g['passing'] for g in all_stats if 'passing' in g and not g['passing'].empty]),
                'rushing': pd.concat([g['rushing'] for g in all_stats if 'rushing' in g and not g['rushing'].empty]),
                'receiving': pd.concat([g['receiving'] for g in all_stats if 'receiving' in g and not g['receiving'].empty])
            }
            
            # Merge all stats together
            master = pd.merge(combined_stats['passing'], combined_stats['rushing'], 
                            how='outer', on='player', suffixes=('_pass', '_rush'))
            master = pd.merge(master, combined_stats['receiving'], how='outer', on='player')
            
            # Consolidate team information from all stat types
            def consolidate_team(row):
                # Try to get team from any of the team columns
                teams = []
                if 'team_pass' in row and pd.notna(row['team_pass']) and row['team_pass'] != '':
                    teams.append(row['team_pass'])
                if 'team_rush' in row and pd.notna(row['team_rush']) and row['team_rush'] != '':
                    teams.append(row['team_rush'])
                if 'team' in row and pd.notna(row['team']) and row['team'] != '':
                    teams.append(row['team'])
                
                # Return the first non-empty team, or 'Unknown' if none found
                if teams:
                    return teams[0]
                else:
                    return 'Unknown'
            
            master['team'] = master.apply(consolidate_team, axis=1)
            
            # Drop the old team columns
            columns_to_drop = [col for col in master.columns if col.startswith('team_')]
            if columns_to_drop:
                master = master.drop(columns=columns_to_drop)
            
            # Clean up and format raw stats
            master = master.fillna(0)
            master = self.clean_raw_stats(master)
            
            print(f"\nSuccessfully processed {len(all_stats)} games")
            return master
            
        except Exception as e:
            print(f"Error processing games: {e}")
            raise
            
    def clean_raw_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and format raw stats without DFS scoring conversion"""
        # Define expected raw stat columns
        raw_stat_columns = [
            'pass_Yds', 'pass_TD', 'pass_INT', 'pass_Att', 'pass_Cmp',
            'rush_Yds', 'rush_TD', 'rush_Att', 
            'rec_Rec', 'rec_Yds', 'rec_TD', 'rec_Tar'
        ]
        
        # Ensure all required columns exist
        for col in raw_stat_columns:
            if col not in df.columns:
                print(f"Missing column {col}, adding with zeros")
                df[col] = 0
        
        # Ensure team column exists
        if 'team' not in df.columns:
            print("Missing team column, adding empty values")
            df['team'] = ''
        
        # Convert all stat columns to numeric, replacing any non-numeric values with 0
        print("\nCleaning raw stats for columns:", raw_stat_columns)
        for col in raw_stat_columns:
            try:
                # Convert to numeric, replacing any non-numeric values with 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            except Exception as e:
                print(f"Error cleaning stats for {col}: {e}")
                df[col] = 0
        
        # Clean up final DataFrame
        df.rename(columns={"player": "Name"}, inplace=True)
        df["Name"] = df["Name"].apply(clean_player_name)
        
        # Reorder columns to put Name and Team first, then organize by stat type
        column_order = ["Name", "team"] + raw_stat_columns
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
        
        print("\nFinal columns:", df.columns.tolist())
        return df

    def save_box_scores_to_database(self, df: pd.DataFrame) -> bool:
        """Save box score data to the database instead of CSV"""
        try:
            if df.empty:
                print("⚠️ No box score data to save")
                return False
            
            print(f"💾 Saving {len(df)} box score records to database...")
            
            with self.db_manager.get_session() as session:
                # Get all games for this week to map team names to game IDs
                games = session.query(Game).filter(Game.week == self.week).all()
                game_lookup = {}
                
                for game in games:
                    # Create lookup by team names (both home and away)
                    game_lookup[game.home_team] = game.id
                    game_lookup[game.away_team] = game.id
                
                print(f"📊 Found {len(games)} games for Week {self.week}")
                
                # Clear existing box scores for this week to avoid duplicates
                deleted_count = session.query(BoxScore).filter(BoxScore.week == self.week).delete()
                if deleted_count > 0:
                    print(f"🔄 Cleared {deleted_count} existing box score records for Week {self.week}")
                
                saved_count = 0
                for _, row in df.iterrows():
                    player_name = row.get('Name', '')
                    team = row.get('team', '')
                    
                    if not player_name or player_name == 'Unknown':
                        continue
                    
                    # Find game_id for this player's team
                    game_id = game_lookup.get(team)
                    if not game_id:
                        print(f"⚠️ No game found for team '{team}' - skipping player {player_name}")
                        continue
                    
                    # Save each stat type as a separate box score record
                    # Map to the standard stat types used in the system
                    stat_mappings = {
                        'pass_Yds': 'Passing Yards',
                        'pass_TD': 'Passing TDs', 
                        'pass_INT': 'Passing Interceptions',
                        'rush_Yds': 'Rushing Yards',
                        'rush_TD': 'Rushing TDs',
                        'rec_Rec': 'Receptions',
                        'rec_Yds': 'Receiving Yards',
                        'rec_TD': 'Receiving TDs'
                    }
                    
                    for stat_col, stat_type in stat_mappings.items():
                        if stat_col in row and pd.notna(row[stat_col]) and row[stat_col] != 0:
                            try:
                                actual_result = float(row[stat_col])
                                
                                box_score = BoxScore(
                                    game_id=game_id,
                                    player=player_name,
                                    stat_type=stat_type,
                                    actual_result=actual_result,
                                    week=self.week,
                                    team=team
                                )
                                session.add(box_score)
                                saved_count += 1
                                
                            except (ValueError, TypeError) as e:
                                print(f"⚠️ Error converting {stat_col} value '{row[stat_col]}' for {player_name}: {e}")
                                continue
                
                session.commit()
                print(f"✅ Successfully saved {saved_count} box score records to database")
                return True
                
        except Exception as e:
            print(f"❌ Error saving box scores to database: {e}")
            import traceback
            traceback.print_exc()
            return False

def main(argv):
    """Main function for NFL box score scraping and database storage"""
    parser = argparse.ArgumentParser(description='Scrape NFL box scores and save to database')
    parser.add_argument("weeks", type=int, nargs='+', help="NFL Week(s) - can specify multiple weeks")
    args = parser.parse_args()
    
    try:
        # Test database connection first
        print("🔍 Testing database connection...")
        db_manager = DatabaseManager()
        if not db_manager.test_connection():
            print("❌ Database connection failed. Please check your database configuration.")
            sys.exit(1)
        print("✅ Database connection successful")
        
        # Process each week
        for week in args.weeks:
            print(f"\n{'='*50}")
            print(f"Processing Week {week}")
            print(f"{'='*50}")
            
            scraper = FootballDBScraper(week)
            driver = scraper.setup_driver()
            
            try:
                master_df = scraper.process_all_games()
                
                if not master_df.empty:
                    # Save to database instead of CSV
                    success = scraper.save_box_scores_to_database(master_df)
                    if success:
                        print(f"\n✅ Successfully saved Week {week} box scores to database")
                    else:
                        print(f"\n❌ Failed to save Week {week} box scores to database")
                else:
                    print(f"\n⚠️ No box score data found for Week {week}")
                
            except Exception as e:
                print(f"\nError processing week {week}: {e}")
                continue
                
            finally:
                if driver:
                    driver.quit()
        
        print(f"\n{'='*50}")
        print(f"Completed processing {len(args.weeks)} week(s): {args.weeks}")
        print(f"Box score data saved to database")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])