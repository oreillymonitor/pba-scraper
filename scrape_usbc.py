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
    text = " ".join(text.split()).strip()
    # Normalize times: 7 p.m. -> 7 PM
    text = re.sub(r'(\d+)\s*p(?![mM])(?:\.m\.)?', r'\1 PM', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d+)\s*a(?![mM])(?:\.m\.)?', r'\1 AM', text, flags=re.IGNORECASE)
    return text

def parse_iso_time(date_str, clean_time):
    if not date_str:
        return None
    try:
        month_map = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        m = re.search(r'([A-Za-z]+)\.?\s*(\d+)', date_str)
        if not m:
            return None
        month_name = m.group(1)[:3].lower()
        if month_name not in month_map:
            return None
        mo = month_map[month_name]
        day_num = int(m.group(2))
        hr = 12
        mn = 0
        if clean_time and clean_time != 'TBD':
            t_m = re.search(r'(\d+)(?::(\d+))?\s*(AM|PM)', clean_time)
            if t_m:
                hr = int(t_m.group(1))
                mn = int(t_m.group(2)) if t_m.group(2) else 0
                if t_m.group(3).upper() == 'PM' and hr < 12:
                    hr += 12
                elif t_m.group(3).upper() == 'AM' and hr == 12:
                    hr = 0
        return f"2026{mo:02d}{day_num:02d}T{hr:02d}{mn:02d}00Z"
    except Exception:
        return None

def parse_section_schedule(soup):
    article = soup.find('article', class_='article--detail')
    sec = article.find('section') if article else soup.find('section')
    if not sec:
        return []

    # Group elements by <hr> tags
    blocks = []
    curr = []
    for c in sec.children:
        if getattr(c, 'name', None) == 'hr':
            if curr:
                blocks.append(curr)
                curr = []
        else:
            curr.append(c)
    if curr:
        blocks.append(curr)

    schedule = []
    for b in blocks:
        txt = ' '.join(c.get_text(' ', strip=True) if hasattr(c, 'get_text') else str(c).strip() for c in b)
        if not any(k in txt for k in ['PBA', 'PWBA', 'USBC', 'Regional', 'Championship', 'Showdown']):
            continue
            
        strongs = [c for c in b if getattr(c, 'name', None) == 'strong']
        if not strongs:
            continue
            
        header_raw = strongs[0].get_text(' ', strip=True)
        # Remove parenthetical notes
        header_clean = re.sub(r'\(All listed times.*?\)', '', header_raw, flags=re.IGNORECASE).strip()
        
        parts = header_clean.split(' - ')
        if len(parts) >= 2:
            date_str = parts[0].strip()
            tourn_str = ' - '.join(parts[1:]).strip()
        else:
            date_str = header_clean
            tourn_str = header_clean

        # Extract times from <li> elements
        li_tags = [li for c in b if hasattr(c, 'find_all') for li in c.find_all('li')]
        time_strs = [li.get_text(' ', strip=True) for li in li_tags]
        main_time = ''
        if time_strs:
            finals_times = [t for t in time_strs if any(k in t.lower() for k in ['stepladder', 'match play', 'finals', 'championship'])]
            main_time = finals_times[-1] if finals_times else time_strs[-1]
        elif 'Times will be available at a later date' in txt:
            main_time = 'TBD'

        clean_time = ''
        t_match = re.search(r'(\d+(?::\d+)?\s*(?:a\.m\.|p\.m\.|AM|PM)|Noon)', main_time, re.IGNORECASE)
        if t_match:
            tm = t_match.group(1).replace('Noon', '12 PM')
            tm = re.sub(r'(\d+)\s*p\.?m\.?', r'\1 PM', tm, flags=re.IGNORECASE)
            tm = re.sub(r'(\d+)\s*a\.?m\.?', r'\1 AM', tm, flags=re.IGNORECASE)
            clean_time = tm
        elif main_time == 'TBD':
            clean_time = 'TBD'

        # Extract broadcaster info
        imgs = [img for c in b if hasattr(c, 'find_all') for img in c.find_all('img')]
        channels = []
        logos = []
        for im in imgs:
            alt = im.get('alt', '')
            src = im.get('src', '')
            if 'bowltv' in src.lower() or 'bowltv' in alt.lower():
                if 'BowlTV' not in channels:
                    channels.append('BowlTV')
                    logos.append(src)
            elif 'bowlingtv' in src.lower() or 'bowling tv' in alt.lower():
                if 'Bowling TV' not in channels:
                    channels.append('Bowling TV')
                    logos.append(src)
            elif 'cbs' in src.lower() or 'cbs' in alt.lower():
                if 'CBS Sports Network' not in channels:
                    channels.append('CBS Sports Network')
                    logos.append(src)
            elif 'cw' in src.lower() or 'cw' in alt.lower():
                if 'The CW' not in channels:
                    channels.append('The CW')
                    logos.append(src)

        ch_str = ', '.join(channels) if channels else 'BowlTV'
        ch_logo = logos[0] if logos else 'https://images.bowl.com/bowl/media/assets/usbc/the sport of bowling show/bowltv_125.png'
        ev_type = 'Regional' if 'regional' in tourn_str.lower() else 'Professional'
        start_iso = parse_iso_time(date_str, clean_time)

        schedule.append({
            'tournament': tourn_str,
            'tour': 'usbc',
            'type': ev_type,
            'channel': ch_str,
            'channel_logo': ch_logo,
            'date': date_str,
            'time': clean_time,
            'start_time': start_iso,
            'timezone': 'ET',
            'location': 'See Event Details'
        })
    return schedule

def parse_table_schedule(soup):
    table = soup.find('table')
    if not table:
        return []
        
    logo_mapping = {
        "bowltv": ("BowlTV", "https://images.bowl.com/bowl/media/assets/bowlers/television/bowltv-tv-schedule.svg"),
        "cw_logo": ("The CW", "https://images.bowl.com/bowl/media/assets/bowlers/television/cw_logo_cw_black.png"),
        "cbs": ("CBS Sports Network", "https://www.pba.com/sites/pba/files/2023-05/cbs-sports-network.png"),
        "fox": ("FOX", "https://www.pba.com/sites/pba/files/2023-05/fox-sports.png"),
        "fs1": ("FS1", "https://www.pba.com/sites/pba/files/2023-05/fs1.png")
    }

    rows = table.find_all('tr')
    schedule = []
    for row in rows:
        cols = [td for td in row.find_all('td') if clean_text(td.get_text()) or td.find('img')]
        if len(cols) < 3:
            continue
        if "Date" in cols[0].get_text() and "Event" in cols[1].get_text():
            continue

        raw_date_time = clean_text(cols[0].get_text())
        event = clean_text(cols[1].get_text())
        raw_network = clean_text(cols[2].get_text())

        time_match = re.search(r'(\d+(?::\d+)?\s*(?:AM|PM|a\.m\.|p\.m\.|ET|CT|PT|MT))', raw_date_time, re.IGNORECASE)
        if not time_match:
            time_match = re.search(r'(\d+(?::\d+)?\s*(?:AM|PM|a\.m\.|p\.m\.|ET|CT|PT|MT))', raw_network, re.IGNORECASE)

        if time_match:
            time = time_match.group(1).strip()
            date_label = raw_date_time.replace(time, "").strip().replace("  ", " ")
        else:
            date_label = raw_date_time
            time = ""

        if not event:
            continue

        # Check logo images
        imgs = row.find_all('img')
        channel = "Unknown"
        channel_logo = None
        for img in imgs:
            src = img.get('src', '').lower()
            for key, (name, logo) in logo_mapping.items():
                if key in src:
                    channel = name
                    channel_logo = logo
                    break
            if channel != "Unknown":
                break

        event_type = "Professional"
        event_lower = event.lower()
        if "intercollegiate" in event_lower or "college" in event_lower:
            event_type = "College"
        elif "junior gold" in event_lower or "youth" in event_lower:
            event_type = "Youth"

        start_iso = None
        if date_label and time:
            try:
                date_str = f"{date_label} 2026 {time}"
                dt = datetime.strptime(date_str, "%B %d %Y %I:%M %p")
                start_iso = dt.strftime("%Y%m%dT%H%M00Z")
            except Exception:
                try:
                    date_str = f"{date_label} 2026 {time}"
                    dt = datetime.strptime(date_str, "%B %d %Y %I %p")
                    start_iso = dt.strftime("%Y%m%dT%H%M00Z")
                except Exception:
                    pass

        schedule.append({
            "tournament": event,
            "tour": "usbc",
            "type": event_type,
            "channel": channel,
            "channel_logo": channel_logo,
            "date": date_label,
            "time": time,
            "start_time": start_iso,
            "timezone": "ET",
            "location": "See Event Details"
        })
    return schedule

def scrape_usbc_schedule():
    candidate_urls = [
        "https://bowl.com/broadcast-schedule",
        "https://bowl.com/tv-schedule"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }

    for url in candidate_urls:
        print(f"[{datetime.now()}] Fetching {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                print(f"INFO: {url} returned HTTP {response.status_code}. Trying next candidate...")
                continue
        except requests.exceptions.RequestException as e:
            print(f"WARNING: Request to {url} failed: {e}. Trying next candidate...")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try table parser first if table exists
        events = parse_table_schedule(soup)
        if events:
            print(f"SUCCESS: Extracted {len(events)} events from table on {url}")
            return events

        # Try section / article parser
        events = parse_section_schedule(soup)
        if events:
            print(f"SUCCESS: Extracted {len(events)} events from section on {url}")
            return events

    print("WARNING: Could not extract schedule events from candidate URLs.")
    return None

if __name__ == "__main__":
    output_file = "usbc_tv_schedule.json"
    existing_events = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_events = json.load(f)
            print(f"INFO: Loaded {len(existing_events)} existing events from {output_file}")
        except Exception as e:
            print(f"WARNING: Could not read existing {output_file}: {e}")

    new_events = scrape_usbc_schedule()

    if new_events is None or len(new_events) == 0:
        if len(existing_events) > 0:
            print(f"INFO: Scraper returned no new events. Preserving {len(existing_events)} existing events.")
            sys.exit(0)
        else:
            print("WARNING: No events scraped and no existing data available.")
            sys.exit(0)

    # Merge newly scraped events with existing events to preserve past season tournaments
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
        print(f"SUCCESS: Saved {len(merged)} total merged events to {output_file}")
    except Exception as e:
        print(f"CRITICAL: Failed to write output file: {e}")
        sys.exit(1)
