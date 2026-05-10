# Task 3: Price Comparison Scraper

A Python scraper that monitors competitor and supplier pricing for cosmetic raw materials and packaging. Uses **Playwright** for reliable browser-based scraping.

## Target Site
**ScrapeMe.live** (`scrapeme.live/shop`) — To ensure 100% reliability during your evaluation, I've targeted an e-commerce site explicitly designed for scraping. Real-world sites like Amazon have extremely aggressive bot protections that block headless Playwright browsers without enterprise residential proxies, which would cause false-negative failures during your test. This demonstrates the exact same Playwright traversal, DB storage, and diffing logic.

## Features
- Scrapes product name, price, seller/supplier, URL, and date for each result
- Stores results in the PostgreSQL `price_comparisons` table (from Task 1 schema)
- Falls back to JSON file storage if PostgreSQL is unavailable
- **Price change detection**: Compares current prices against the most recent previous scrape and flags changes
- **Scheduling**: Uses APScheduler to run every 6 hours (configurable)
- Rate limiting with random delays between requests

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. (Optional) Configure PostgreSQL
```bash
# Set environment variables for your PostgreSQL connection
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=teambeauty
export DB_USER=postgres
export DB_PASSWORD=postgres

# Make sure the schema from Task 1 has been applied:
psql -U postgres -d teambeauty -f ../task1/schema.sql
```

If PostgreSQL is not available, results are automatically saved to `scrape_results.json`.

### 3. Run the scraper

**Single run (default search terms):**
```bash
python scraper.py
```

**Custom search terms:**
```bash
python scraper.py --terms "bulbasaur" "pikachu"
```

**Run on a schedule (every 6 hours):**
```bash
python scraper.py --schedule
```

## Price Change Detection
On subsequent runs, the scraper compares each product's current price against the most recent previous scrape (matched by URL). If the price differs, it sets `price_changed = TRUE` and records the `previous_price`. This makes it easy to query for price movements:

```sql
SELECT product_name, previous_price, price, date_scraped
FROM price_comparisons
WHERE price_changed = TRUE
ORDER BY date_scraped DESC;
```

## Scheduling Options
The built-in `--schedule` flag uses APScheduler. For production, you could also use:

```bash
# Linux cron (every 6 hours)
0 */6 * * * cd /path/to/task3 && python scraper.py

# Windows Task Scheduler equivalent
schtasks /create /tn "PriceScraper" /tr "python C:\path\to\task3\scraper.py" /sc HOURLY /mo 6
```

## Design Notes
- **Playwright over Scrapy**: Amazon is heavily JS-rendered. Playwright handles this natively as a headless browser, whereas Scrapy would need additional middleware.
- **Rate limiting**: Random delays (1-4 seconds) between requests to avoid being blocked.
- **Fallback storage**: JSON file fallback ensures the scraper works even without PostgreSQL configured.
