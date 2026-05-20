# PBA & PWBA TV Schedule Scraper

This project automatically scrapes the official PBA and PWBA TV schedules and provides them as structured JSON files.

## Features
- **Precise Timing (PBA):** Extracts ISO 8601 start/end times from calendar metadata.
- **Wikipedia Sourced (PWBA):** Extracts the 2026 PWBA tour schedule from Wikipedia.
- **Clean Channel Names:** Maps broadcaster logos to human-readable names (e.g., FOX, FS1, CBS Sports, BowlTV).
- **Automated Updates:** Uses GitHub Actions to refresh the data every day at midnight UTC.

## Output Files
The resulting data is saved to the following files in the root of the repository:
- `pba_tv_schedule.json`
- `pwba_tv_schedule.json`

### Sample PWBA Entry
```json
{
    "tournament": "USBC Queens",
    "location": "Las Vegas, NV",
    "channel": "CBS Sports Network",
    "channel_logo": "https://www.pba.com/sites/pba/files/2023-05/cbs-sports-network.png",
    "date_label": "May 19",
    "start_time": null,
    "end_time": null,
    "timezone": "ET"
}
```

## Setup & Maintenance
- **PBA Scraper:** `scrape_pba.py`
- **PWBA Scraper:** `scrape_pwba.py`
- **Automation:** `.github/workflows/scrape.yml`
- **Requirements:** `requirements.txt`
