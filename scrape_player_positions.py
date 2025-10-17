"""
Web scraper to extract player positional information from footballdb.com
This script will navigate through all last name letters and extract player data.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import sys

# Add the current directory to the path so we can import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import clean_player_name

class FootballDBPlayerScraper:
    def __init__(self):
        self.base_url = "https://www.footballdb.com"
        self.players_url = "https://www.footballdb.com/players/index.html"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.players_data = []
        
    def convert_name_format(self, name):
        """Convert 'Last, First' format to 'First Last' format"""
        if ',' in name:
            parts = name.split(',', 1)
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip()
                return f"{first_name} {last_name}"
        return name
    
    def _detect_max_page(self, soup):
        """Detect the maximum page number from pagination"""
        try:
            # Look for pagination links
            pagination_links = soup.find_all('a', href=True)
            max_page = 1
            
            for link in pagination_links:
                href = link.get('href', '')
                if 'page=' in href:
                    try:
                        # Extract page number from href like "?letter=M&page=3"
                        page_part = href.split('page=')[1]
                        page_num = int(page_part.split('&')[0])
                        max_page = max(max_page, page_num)
                    except (ValueError, IndexError):
                        continue
            
            return max_page
        except Exception as e:
            print(f"Error detecting pagination: {e}")
            return 1  # Default to 1 page if detection fails
    
    def get_letter_links(self, test_mode=False):
        """Generate letter links by looping through the alphabet"""
        if test_mode:
            # Test with just a few letters first
            letters = 'ABC'
        else:
            letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        letter_links = []
        
        for letter in letters:
            letter_url = f"{self.players_url}?letter={letter}"
            letter_links.append((letter, letter_url))
        
        print(f"Generated {len(letter_links)} letter links")
        return letter_links
    
    def scrape_players_for_letter(self, letter, letter_url):
        """Scrape all players for a specific letter, handling pagination"""
        try:
            print(f"Scraping letter: {letter} - {letter_url}")
            
            # First, get the first page to detect pagination
            response = self.session.get(letter_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for pagination
            max_page = self._detect_max_page(soup)
            
            players = []
            
            # Scrape all pages for this letter
            for page in range(1, max_page + 1):
                if page == 1:
                    # Use the soup we already have for page 1
                    current_soup = soup
                else:
                    # Get additional pages
                    page_url = f"{letter_url}&page={page}"
                    print(f"  Scraping page {page} of {max_page}")
                    response = self.session.get(page_url)
                    response.raise_for_status()
                    current_soup = BeautifulSoup(response.content, 'html.parser')
                    time.sleep(0.5)  # Be respectful between page requests
                
                # Find the table containing player data
                table = current_soup.find('table', {'class': 'statistics'})
                if not table:
                    print(f"No table found for letter {letter}, page {page}")
                    continue
                
                rows = table.find_all('tr')[1:]  # Skip header row
                
                # Process players from this page
                for row in rows:
                    try:
                        cells = row.find_all('td')
                        if len(cells) < 3:  # Need at least name, position, team
                            continue
                        
                        # Extract player information
                        name_cell = cells[0]
                        name_link = name_cell.find('a')
                        if not name_link:
                            # Try to get name from cell text if no link
                            raw_player_name = name_cell.text.strip()
                            player_url = ''
                        else:
                            raw_player_name = name_link.text.strip()
                            player_url = name_link.get('href', '')
                        
                        if not raw_player_name:
                            continue
                        
                        # Convert from "Last, First" to "First Last" format
                        formatted_name = self.convert_name_format(raw_player_name)
                        
                        # Clean the name using the existing clean_player_name function
                        cleaned_name = clean_player_name(formatted_name)
                        
                        # Position is in the second column
                        position = cells[1].text.strip() if len(cells) > 1 else ''
                        
                        # Team is in the third column
                        team = cells[2].text.strip() if len(cells) > 2 else ''
                        
                        # College is in the fourth column (if exists)
                        college = cells[3].text.strip() if len(cells) > 3 else ''
                        
                        player_data = {
                            'raw_name': raw_player_name,
                            'formatted_name': formatted_name,
                            'cleaned_name': cleaned_name,
                            'position': position,
                            'team': team,
                            'college': college,
                            'url': player_url
                        }
                        
                        players.append(player_data)
                        
                    except Exception as e:
                        print(f"Error processing row in letter {letter}, page {page}: {e}")
                        continue
            
            print(f"Found {len(players)} players for letter {letter} across {max_page} page(s)")
            return players
            
        except Exception as e:
            print(f"Error scraping letter {letter}: {e}")
            return []
    
    def scrape_all_players(self):
        """Scrape all players from all letters"""
        print("Starting to scrape all players from footballdb.com...")
        
        # Get all letter links
        letter_links = self.get_letter_links(test_mode=False)
        if not letter_links:
            print("No letter links found. Exiting.")
            return []
        
        all_players = []
        
        for letter, letter_url in letter_links:
            try:
                players = self.scrape_players_for_letter(letter, letter_url)
                all_players.extend(players)
                
                # Be respectful - add a small delay between requests
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing letter {letter}: {e}")
                continue
        
        print(f"Total players scraped: {len(all_players)}")
        return all_players
    
    def save_to_csv(self, players_data, filename="player_positions.csv"):
        """Save player data to CSV file"""
        if not players_data:
            print("No player data to save")
            return
        
        df = pd.DataFrame(players_data)
        
        # Create 2025 directory if it doesn't exist
        os.makedirs("2025", exist_ok=True)
        
        filepath = os.path.join("2025", filename)
        df.to_csv(filepath, index=False)
        print(f"Saved {len(players_data)} players to {filepath}")
        
        # Print some statistics
        print(f"\nPosition distribution:")
        print(df['position'].value_counts())
        
        print(f"\nTeam distribution (top 10):")
        print(df['team'].value_counts().head(10))
        
        return filepath

def main():
    """Main function to run the scraper"""
    scraper = FootballDBPlayerScraper()
    
    try:
        # Scrape all players
        players_data = scraper.scrape_all_players()
        
        if players_data:
            # Save to CSV
            csv_path = scraper.save_to_csv(players_data)
            print(f"\n✅ Successfully scraped and saved player data to {csv_path}")
        else:
            print("❌ No player data was scraped")
            
    except Exception as e:
        print(f"❌ Error during scraping: {e}")

if __name__ == "__main__":
    main()
