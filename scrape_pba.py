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
    text = " ".join(text.split()).strip()
    
    # Normalize times: 1p -> 1 PM, 11a -> 11 AM
    text = re.sub(r'(\d+)\s*p(\.m\.)?', r'\1 PM', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+)\s*a(\.m\.)?', r'\1 AM', text, flags=re.IGNORECASE)
    return text

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
    # The PBA site often displays a "No upcoming events" or "There are No Events to Show" message
    empty_pattern = re.compile(
        r"no upcoming events|no events to show|stay tuned for more events|no events found|check back soon",
        re.IGNORECASE
    )
    empty_msg = soup.find(string=empty_pattern)
    if empty_msg:
        print(f"INFO: PBA off-season detected: '{empty_msg.strip()}'.")
        return []

    # Locate the main schedule table
    table = soup.find('table', class_='mobile-stacked')
    if not table:
        table = soup.find('table')
    if not table:
        print("WARNING: Could not find the schedule table. Structure might have changed.")
        return None
    
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
            
            # Split time_label into date and time
            # Example: "Jan 19 5 PM"
            time_match = re.search(r'(\d+(?::\d+)?\s*(?:AM|PM))', time_label, re.IGNORECASE)
            if time_match:
                time = time_match.group(1).strip()
                date = time_label.replace(time, "").strip()
            else:
                date = time_label
                time = ""

            schedule.append({
                "tournament": tournament,
                "tour": "pba",
                "channel": channel_name,
                "channel_logo": channel_logo,
                "date": date,
                "time": time,
                "start_time": start_iso,
                "timezone": "ET",
                "location": "See Event Details"
            })
        except Exception as e:
            print(f"WARNING: Skipping row due to error: {e}")
            continue
    
    return schedule

if __name__ == "__main__":
    output_file = "pba_tv_schedule.json"
    existing_events = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_events = json.load(f)
            print(f"INFO: Loaded {len(existing_events)} existing events from {output_file}")
        except Exception as e:
            print(f"WARNING: Could not read existing {output_file}: {e}")

    new_events = scrape_pba_tv_schedule()
    
    if new_events is None:
        print("WARNING: PBA scraper failed or structure changed. Preserving existing schedule data.")
        sys.exit(0)
    
    # Handle off-season: preserve existing events so historical schedule remains viewable
    if len(new_events) == 0:
        print("INFO: Resulting schedule is empty (off-season). Preserving existing data so historical events remain accessible.")
        if len(existing_events) > 0:
            print(f"INFO: Preserved {len(existing_events)} existing events in {output_file}")
            sys.exit(0)
        else:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=4)
            except Exception as e:
                print(f"CRITICAL: Failed to write output file: {e}")
            sys.exit(0)

    # Merge newly scraped events with existing events
    merged = list(existing_events)
    for new_e in new_events:
        n_title = re.sub(r'[^a-z0-9]', '', new_e['tournament'].lower())
        n_date = re.sub(r'[^a-z0-9]', '', new_e['date'].lower())
        match = None
        for ex in merged:
            e_title = re.sub(r'[^a-z0-9]', '', ex['tournament'].lower())
            e_date = re.sub(r'[^a-z0-9]', '', ex['date'].lower())
            if n_title == e_title or (n_date in e_date and n_title in e_title):
                match = ex
                break
        if match:
            match.update(new_e)
        else:
            merged.append(new_e)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged, f, indent=4, ensure_ascii=False)
        print(f"SUCCESS: Saved {len(merged)} events to {output_file}")
    except Exception as e:
        print(f"CRITICAL: Failed to write output file: {e}")
        sys.exit(1)

