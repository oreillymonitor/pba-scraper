# PBA, PWBA & USBC TV Schedule Scraper

This project automatically scrapes the official PBA, PWBA, and USBC TV schedules and provides them as structured JSON files.

**[Live Unified Schedule](https://oreillymonitor.github.io/pba-scraper/)**

## Features
- **Precise Timing (PBA):** Extracts ISO 8601 start/end times from calendar metadata.
- **Wikipedia Sourced (PWBA):** Extracts the 2026 PWBA tour schedule from Wikipedia.
- **USBC Schedule (College & Youth):** Scrapes `bowl.com` for collegiate and televised USBC events.
- **Clean Channel Names:** Maps broadcaster logos to human-readable names (e.g., FOX, FS1, CBS Sports, BowlTV, The CW).
- **Automated Updates:** Uses GitHub Actions to refresh the data every day at midnight UTC.

## Output Files
The resulting data is saved to the following files in the root of the repository:
- `pba_tv_schedule.json`
- `pwba_tv_schedule.json`
- `usbc_tv_schedule.json`

### Sample USBC Entry
```json
{
    "tournament": "Intercollegiate Team Championships (Men)",
    "channel": "CBS Sports Network",
    "channel_logo": "https://images.bowl.com/bowl/media/assets/temp/cbs-logo-white.svg",
    "date_label": "May 13 7 p.m.",
    "start_time": null,
    "end_time": null,
    "timezone": "ET"
}
```

## Setup & Maintenance
- **PBA Scraper:** `scrape_pba.py`
- **PWBA Scraper:** `scrape_pwba.py`
- **USBC Scraper:** `scrape_usbc.py`
- **Automation:** `.github/workflows/scrape.yml`
- **Requirements:** `requirements.txt`
