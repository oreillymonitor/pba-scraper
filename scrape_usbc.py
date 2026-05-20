import requests
from bs4 import BeautifulSoup
import json
import re
import sys
from datetime import datetime

def clean_text(text):
    if not text:
        return ""
    text = " ".join(text.split()).strip()
    
    # Normalize times: 7 p.m. -> 7 PM
    text = re.sub(r'(\d+)\s*p(\.m\.)?', r'\1 PM', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+)\s*a(\.m\.)?', r'\1 AM', text, flags=re.IGNORECASE)
    return text

def get_network_info(row):
    # Search for logos in the row
    imgs = row.find_all('img')
    networks = []
    
    logo_mapping = {
        "bowltv": ("BowlTV", "https://images.bowl.com/bowl/media/assets/bowlers/television/bowltv-tv-schedule.svg"),
        "cw_logo": ("The CW", "https://images.bowl.com/bowl/media/assets/bowlers/television/cw_logo_cw_black.png"),
        "cbs": ("CBS Sports Network", "https://www.pba.com/sites/pba/files/2023-05/cbs-sports-network.png"),
        "fox": ("FOX", "https://www.pba.com/sites/pba/files/2023-05/fox-sports.png"),
        "fs1": ("FS1", "https://www.pba.com/sites/pba/files/2023-05/fs1.png")
    }
    
    for img in imgs:
        src = img.get('src', '').lower()
        for key, (name, logo) in logo_mapping.items():
            if key in src:
                networks.append({"name": name, "logo": logo})
                
    if not networks:
        return "Unknown", None
        
    # Prefer TV Finals over BowlTV if both exist in the row for the "channel" field
    # but we can return the first one found or the one that looks like a major network
    for net in networks:
        if net["name"] != "BowlTV":
            return net["name"], net["logo"]
            
    return networks[0]["name"], networks[0]["logo"]

def scrape_usbc_schedule():
    url = "https://bowl.com/tv-schedule"
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
    
    table = soup.find('table')
    if not table:
        print("WARNING: Could not find the schedule table.")
        return []

    rows = table.find_all('tr')
    schedule = []
    
    for row in rows:
        # Filter out rows that are clearly headers or empty
        cols = [td for td in row.find_all('td') if clean_text(td.get_text()) or td.find('img')]
        
        if len(cols) < 3:
            continue
            
        # Check if this is the header row
        if "Date" in cols[0].get_text() and "Event" in cols[1].get_text():
            continue
            
        try:
            # USBC often puts both date and time in the first column
            raw_date_time = clean_text(cols[0].get_text())
            event = clean_text(cols[1].get_text())
            
            # Use regex to split "March 8 4 PM" into "March 8" and "4 PM"
            time_match = re.search(r'(\d+(?::\d+)?\s*(?:AM|PM))', raw_date_time, re.IGNORECASE)
            if time_match:
                time = time_match.group(1).strip()
                date_label = raw_date_time.replace(time, "").strip()
            else:
                date_label = raw_date_time
                time = ""
            
            # If date or event is empty, it might be a continuation of the previous row
            if not event:
                continue
                
            channel, channel_logo = get_network_info(row)
            
            # Determine event type
            event_type = "Professional"
            event_lower = event.lower()
            if "intercollegiate" in event_lower or "college" in event_lower:
                event_type = "College"
            elif "junior gold" in event_lower or "youth" in event_lower:
                event_type = "Youth"
            
            schedule.append({
                "tournament": event,
                "type": event_type,
                "channel": channel,
                "channel_logo": channel_logo,
                "date": date_label,
                "time": time,
                "date_label": f"{date_label} {time}".strip(),
                "start_time": None,
                "end_time": None,
                "timezone": "ET"
            })
        except Exception as e:
            print(f"WARNING: Skipping row due to error: {e}")
            continue
            
    return schedule

if __name__ == "__main__":
    data = scrape_usbc_schedule()
    
    if data is None:
        print("CRITICAL: Scraper failed.")
        sys.exit(1)
    
    output_file = "usbc_tv_schedule.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"SUCCESS: Saved {len(data)} events to {output_file}")
    except Exception as e:
        print(f"CRITICAL: Failed to write output file: {e}")
        sys.exit(1)
