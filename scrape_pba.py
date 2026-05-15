import requests
from bs4 import BeautifulSoup
import json
import re
import os
import sys
from datetime import datetime

def clean_text(text):
    if not text:
        return ""
    # Remove "Broadcast Live" and extra whitespace
    text = text.replace("Broadcast Live", "")
    return " ".join(text.split()).strip()

def get_channel_info(img_tag):
    if not img_tag or not img_tag.get('src'):
        return "Unknown", None
    
    src = img_tag['src']
    full_logo_url = src
    if src.startswith('/'):
        full_logo_url = f"https://www.pba.com{src}"
    
    src_lower = src.lower()
    
    # Mapping common PBA channel logo filenames to clean names
    mapping = {
        "fox": "FOX",
        "fs1": "FS1",
        "fs2": "FS2",
        "cbs-sports": "CBS Sports Network",
        "paramount": "CBS / Paramount+",
        "bowltv": "BowlTV"
    }
    
    channel_name = "Unknown"
    for key, value in mapping.items():
        if key in src_lower:
            channel_name = value
            break
            
    if channel_name == "Unknown":
        # Fallback to the filename if not in mapping
        filename = src_lower.split('/')[-1].split('.')[0]
        channel_name = filename.replace('-', ' ').replace('_', ' ').title()
        
    return channel_name, full_logo_url

def scrape_pba_tv_schedule():
    url = "https://www.pba.com/watch/television"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"[{datetime.now()}] Fetching {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to fetch page: {e}")
        return None # Indicate a network/request failure

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check for off-season messages or empty containers
    # The PBA site often displays a "No upcoming events" message
    empty_msg = soup.find(text=re.compile("No upcoming events", re.IGNORECASE))
    if empty_msg:
        print("INFO: No upcoming events found (Off-season).")
        return []

    # Locate the main schedule table
    table = soup.find('table', class_='mobile-stacked')
    if not table:
        # If no table AND no empty message, the structure might have changed
        print("WARNING: Could not find the schedule table. Structure might have changed.")
        return [] # Return empty list as a safe fallback
    
    tbody = table.find('tbody')
    if not tbody:
        print("INFO: Schedule table exists but is empty.")
        return []

    rows = tbody.find_all('tr')
    print(f"INFO: Found {len(rows)} potential events.")
    
    schedule = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
            
        try:
            # 1. Date/Time Label
            time_label = clean_text(cols[0].get_text())
            
            # 2. Tournament Title
            tournament = clean_text(cols[1].get_text())
            
            # 3. Channel
            channel_name, channel_logo = get_channel_info(cols[2].find('img'))
            
            # 4. Precise ISO Dates from Add to Calendar links
            start_iso = None
            end_iso = None
            
            google_cal = cols[3].find('a', href=re.compile("calendar.google.com"))
            if google_cal:
                href = google_cal['href']
                date_match = re.search(r'dates=(\d{8}T\d{6})/(\d{8}T\d{6})', href)
                if date_match:
                    start_iso = date_match.group(1)
                    end_iso = date_match.group(2)
            
            schedule.append({
                "tournament": tournament,
                "channel": channel_name,
                "channel_logo": channel_logo,
                "date_label": time_label,
                "start_time": start_iso,
                "end_time": end_iso,
                "timezone": "ET"
            })
        except Exception as e:
            print(f"WARNING: Skipping row due to error: {e}")
            continue
    
    return schedule

if __name__ == "__main__":
    data = scrape_pba_tv_schedule()
    
    if data is None:
        print("CRITICAL: Scraper failed due to network/system error. Aborting update to protect existing data.")
        sys.exit(1)
    
    output_file = "pba_tv_schedule.json"
    
    # Optional: Logic to handle off-season (empty list)
    if len(data) == 0:
        print("INFO: Resulting schedule is empty. Updating JSON to reflect off-season.")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"SUCCESS: Saved {len(data)} events to {output_file}")
    except Exception as e:
        print(f"CRITICAL: Failed to write output file: {e}")
        sys.exit(1)

