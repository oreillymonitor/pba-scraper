import requests
from bs4 import BeautifulSoup
import json
import re
import sys
from datetime import datetime

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\[.*?\]', '', text) # Remove citations
    text = " ".join(text.split()).strip()
    
    # Normalize times
    text = re.sub(r'(\d+)\s*p(\.m\.)?', r'\1 PM', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+)\s*a(\.m\.)?', r'\1 AM', text, flags=re.IGNORECASE)
    return text

def get_broadcast_info(tournament_name, notes):
    tournament_lower = tournament_name.lower()
    notes_lower = notes.lower()
    
    # Major tournaments usually on CBS Sports Network
    majors = ["usbc queens", "u.s. women's open", "tour championship"]
    
    is_major = any(major in tournament_lower for major in majors) or "major" in notes_lower
    
    if is_major:
        return "CBS Sports Network", "https://www.pba.com/sites/pba/files/2023-05/cbs-sports-network.png"
    else:
        # Default to BowlTV for standard events
        return "BowlTV", "https://www.pba.com/sites/pba/files/2026-04/bowltv-logo-blk-web.png"

def scrape_pwba_schedule():
    url = "https://en.wikipedia.org/wiki/PWBA_Bowling_Tour:_2026_season"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"[{datetime.now()}] Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch page: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all wikitables
    tables = soup.find_all('table', class_='wikitable')
    if not tables:
        print("WARNING: Could not find any wikitables.")
        return []

    # Identify the schedule table by looking for "Date" and "Tournament" headers
    schedule_table = None
    col_map = {}
    
    for table in tables:
        header_row = table.find('tr')
        if not header_row:
            continue
        headers_text = [clean_text(th.get_text()).lower() for th in header_row.find_all(['th', 'td'])]
        
        is_schedule = ("date" in headers_text or "airdate" in headers_text) and \
                      ("tournament" in headers_text or "event" in headers_text)
        
        if is_schedule:
            schedule_table = table
            for j, h in enumerate(headers_text):
                # Map aliases
                if h == "event": h = "tournament"
                if h == "airdate": h = "date"
                col_map[h] = j
            break
            
    if not schedule_table:
        print("WARNING: Could not identify the schedule table.")
        return []

    rows = schedule_table.find_all('tr')
    schedule = []
    
    # We skip the header row
    for row in rows[1:]:
        cols = row.find_all(['td', 'th'])
        if len(cols) < 2:
            continue
            
        try:
            date_label = clean_text(cols[col_map.get('date', 0)].get_text())
            tournament = clean_text(cols[col_map.get('tournament', 1)].get_text())
            
            # Clean date_label (remove broadcaster names often found in airdate column)
            date_label = re.sub(r'(BowlTV|CBS Sports Network|CBS Sports|FS1|FOX)', '', date_label, flags=re.IGNORECASE).strip()
            
            # City/Location logic
            city_val = ""
            if 'city' in col_map:
                city_val = clean_text(cols[col_map['city']].get_text())
            elif 'location' in col_map:
                city_val = clean_text(cols[col_map['location']].get_text())
            
            state_val = ""
            if 'state' in col_map:
                state_val = clean_text(cols[col_map['state']].get_text())
            
            location = city_val
            if state_val:
                location = f"{city_val}, {state_val}"
            
            notes = ""
            if 'notes' in col_map:
                notes = clean_text(cols[col_map['notes']].get_text())

            channel, channel_logo = get_broadcast_info(tournament, notes)
            
            # If notes didn't have channel info, maybe date_label (original) did
            orig_airdate = clean_text(cols[col_map.get('date', 0)].get_text())
            if "cbs sports" in orig_airdate.lower():
                channel = "CBS Sports Network"
                channel_logo = "https://www.pba.com/sites/pba/files/2023-05/cbs-sports-network.png"
            elif "bowltv" in orig_airdate.lower():
                channel = "BowlTV"
                channel_logo = "https://www.pba.com/sites/pba/files/2026-04/bowltv-logo-blk-web.png"

            schedule.append({
                "tournament": tournament,
                "tour": "pwba",
                "channel": channel,
                "channel_logo": channel_logo,
                "date": date_label,
                "time": "",
                "location": location,
                "start_time": None,
                "timezone": "ET"
            })
        except Exception as e:
            print(f"WARNING: Skipping row due to error: {e}")
            continue
            
    return schedule

if __name__ == "__main__":
    data = scrape_pwba_schedule()
    
    if data is None:
        print("CRITICAL: Scraper failed.")
        sys.exit(1)
    
    output_file = "pwba_tv_schedule.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"SUCCESS: Saved {len(data)} events to {output_file}")
    except Exception as e:
        print(f"CRITICAL: Failed to write output file: {e}")
        sys.exit(1)
