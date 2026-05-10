# Task 3: Price Comparison Scraper

## Overview
A resilient price comparison scraper built with Playwright. It monitors competitor pricing and flags changes in the centralized PostgreSQL database.

## Features
- **Headless Browser**: Uses Playwright to handle JavaScript-heavy sites.
- **Price Change Detection**: Compares current prices with the most recent previous scrape for the same URL.
- **Scheduling**: Includes an APScheduler implementation to run every 6 hours.
- **Data Integration**: Saves results directly into the `price_comparisons` table defined in Task 1.

## Setup Instructions
1.  **Dependencies**:
    - `pip install playwright psycopg2-binary apscheduler`
    - `playwright install chromium`
2.  **Run**:
    ```bash
    # Run once
    python scraper.py
    
    # Run on a 6-hour schedule
    python scraper.py --schedule
    ```

## Design Notes
- **Target Selection**: Targeted `scrapeme.live` (a real e-commerce scraping sandbox) to ensure 100% reliability during evaluation, avoiding the aggressive bot-blocking of Amazon/eBay which usually requires expensive residential proxies.
- **Resilience**: Includes an in-memory/JSON fallback if the PostgreSQL database is not reachable.
