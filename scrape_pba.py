import requests
from bs4 import BeautifulSoup
import json
import re
import os
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
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching page: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    schedule = []
    
    # Locate the main schedule table
    table = soup.find('table', class_='mobile-stacked')
    if not table:
        print("Could not find the schedule table.")
        return []
    
    rows = table.find('tbody').find_all('tr')
    print(f"Found {len(rows)} events.")
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
            
        # 1. Date/Time Label
        time_label = clean_text(cols[0].get_text())
        
        # 2. Tournament Title
        tournament = clean_text(cols[1].get_text())
        
        # 3. Channel
        channel_name, channel_logo = get_channel_info(cols[2].find('img'))
        
        # 4. Precise ISO Dates from Add to Calendar links
        # We look for the Google Calendar link as it contains a clear 'dates' parameter
        start_iso = None
        end_iso = None
        
        google_cal = cols[3].find('a', href=re.compile("calendar.google.com"))
        if google_cal:
            href = google_cal['href']
            # Pattern: dates=20260613T110000/20260613T130000
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
            "timezone": "ET" # PBA site usually defaults to ET
        })
    
    return schedule

if __name__ == "__main__":
    data = scrape_pba_tv_schedule()
    
    output_file = "pba_tv_schedule.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully saved {len(data)} events to {output_file}")
