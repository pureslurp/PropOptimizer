#!/usr/bin/env python3
"""
Scrape player positions from FootballDB and store in database
"""

import requests
from bs4 import BeautifulSoup
import time
from .database_manager import DatabaseManager
from .database_models import PlayerPosition
from utils import clean_player_name
from datetime import datetime

def scrape_players_for_letter(letter):
    """Scrape all players for a given letter"""
    players = []
    page = 1
    
    while True:
        url = f"https://www.footballdb.com/players/index.html?letter={letter}"
        if page > 1:
            url += f"&page={page}"
        
        print(f"  Fetching {url}...")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find player table
            table = soup.find('table', class_='statistics')
            
            if not table:
                print(f"    No table found on page {page}")
                break
            
            # Find all player rows
            rows = table.find_all('tr')[1:]  # Skip header
            
            if not rows:
                print(f"    No players found on page {page}")
                break
            
            print(f"    Found {len(rows)} players on page {page}")
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Extract player info
                    name_cell = cells[0]
                    position_cell = cells[1]
                    team_cell = cells[2] if len(cells) > 2 else None
                    
                    name = name_cell.get_text().strip()
                    position = position_cell.get_text().strip()
                    team = team_cell.get_text().strip() if team_cell else None
                    
                    if name and position:
                        players.append({
                            'player': name,
                            'position': position,
                            'team': team
                        })
            
            # Check if there's a next page
            # Look for pagination links
            pagination = soup.find('div', class_='pagination')
            if pagination:
                next_link = pagination.find('a', text=str(page + 1))
                if next_link:
                    page += 1
                    time.sleep(0.5)  # Be respectful
                    continue
            
            break
            
        except Exception as e:
            print(f"    Error: {e}")
            break
    
    return players

def populate_player_positions():
    """Scrape all players from footballdb.com and populate database"""
    print("🏈 Scraping player positions from FootballDB.com...")
    print()
    
    db_manager = DatabaseManager()
    all_players = []
    
    # Scrape all letters
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    for letter in letters:
        print(f"📝 Processing letter {letter}...")
        players = scrape_players_for_letter(letter)
        all_players.extend(players)
        print(f"   Found {len(players)} players for letter {letter}")
        print()
        time.sleep(1)  # Be respectful between letters
    
    print(f"✅ Total players scraped: {len(all_players)}")
    print()
    
    # Store in database
    print("💾 Storing player positions in database...")
    
    with db_manager.get_session() as session:
        added = 0
        updated = 0
        
        for player_data in all_players:
            player_name = player_data['player']
            cleaned_name = clean_player_name(player_name)
            position = player_data['position']
            team = player_data.get('team')
            
            # Check if player already exists
            existing = session.query(PlayerPosition).filter(
                PlayerPosition.player == player_name
            ).first()
            
            if existing:
                # Update
                existing.position = position
                existing.team = team
                existing.cleaned_name = cleaned_name
                existing.updated_at = datetime.utcnow()
                updated += 1
            else:
                # Insert
                new_player = PlayerPosition(
                    player=player_name,
                    cleaned_name=cleaned_name,
                    position=position,
                    team=team
                )
                session.add(new_player)
                added += 1
            
            # Commit in batches
            if (added + updated) % 100 == 0:
                session.commit()
                print(f"   Processed {added + updated} players...")
        
        session.commit()
    
    print()
    print(f"✅ Complete!")
    print(f"   Added: {added} players")
    print(f"   Updated: {updated} players")
    print(f"   Total: {added + updated} players")
    print()
    
    # Show position breakdown
    with db_manager.get_session() as session:
        from sqlalchemy import func
        
        position_counts = session.query(
            PlayerPosition.position,
            func.count(PlayerPosition.id)
        ).group_by(PlayerPosition.position).all()
        
        print("Position breakdown:")
        for position, count in sorted(position_counts, key=lambda x: x[1], reverse=True):
            print(f"  {position}: {count}")

if __name__ == "__main__":
    populate_player_positions()

