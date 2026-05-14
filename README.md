# PBA TV Schedule Scraper

This project automatically scrapes the official PBA TV schedule and provides it as a structured JSON file.

## Features
- **Precise Timing:** Extracts ISO 8601 start/end times from calendar metadata.
- **Clean Channel Names:** Maps broadcaster logos to human-readable names (e.g., FOX, FS1, CBS Sports).
- **Automated Updates:** Uses GitHub Actions to refresh the data every Sunday at midnight.

## Output File
The resulting data is saved to `pba_tv_schedule.json` in the root of the repository.

### Sample Entry
```json
{
    "tournament": "PBA WSOB XVII - PBA World Championship - Finals",
    "channel": "CBS / Paramount+",
    "date_label": "SAT 6/13 1p ET",
    "start_time": "20260613T130000",
    "end_time": "20260613T150000",
    "timezone": "ET"
}
```

## Setup & Maintenance
- **Scraper:** `pba-scraper/scrape_pba.py`
- **Automation:** `.github/workflows/scrape.yml`
- **Requirements:** `pba-scraper/requirements.txt`
