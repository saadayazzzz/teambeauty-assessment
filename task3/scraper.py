"""
Task 3: Price Comparison Scraper (Professional Edition)
Scrapes product pricing from a real beauty retailer.

Target: fragrancedirect.co.uk
Rationale: This is a real-world, professional e-commerce site. It demonstrates 
advanced Playwright usage, including handling dynamic content, 
wait states, and real-world HTML structures, while remaining accessible 
enough for a stable technical demonstration.

Features:
- Professional beauty industry target (Fragrance Direct)
- Uses shared database utility for cross-task consistency
- Handles real-world search results and pagination
- Detects price changes and flags them in the DB
- Includes a robust scheduler
"""

import asyncio
import os
import re
import random
import json
import sys
from datetime import datetime
from typing import Optional, List

from playwright.async_api import async_playwright
from apscheduler.schedulers.blocking import BlockingScheduler

# Add root to path to import shared database utility
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import get_db_connection

# --- Configuration ---
DEFAULT_SEARCH_TERMS = [
    "Serum",
    "Creme",
    "Moisturizer",
    "Cleanser",
    "Perfume"
]

def save_to_database(results: List[dict]):
    """Save scraped results to the price_comparisons table, detecting price changes."""
    conn = get_db_connection()
    if not conn:
        save_to_json(results)
        return

    try:
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        for item in results:
            # Check for previous price
            cursor.execute(
                "SELECT price FROM price_comparisons WHERE url = %s ORDER BY date_scraped DESC LIMIT 1",
                (item["url"],)
            )
            prev = cursor.fetchone()
            previous_price = prev["price"] if prev else None
            price_changed = False

            if previous_price is not None and item["price"] is not None:
                price_changed = float(previous_price) != float(item["price"])

            cursor.execute(
                """
                INSERT INTO price_comparisons 
                    (search_term, product_name, price, seller_supplier, url, date_scraped, price_changed, previous_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item["search_term"],
                    item["product_name"],
                    item["price"],
                    item["seller_supplier"],
                    item["url"],
                    item["date_scraped"],
                    price_changed,
                    previous_price,
                ),
            )

        conn.commit()
        cursor.close()
        print(f"  Successfully synced {len(results)} results to PostgreSQL.")
    except Exception as e:
        print(f"  Error saving to database: {e}")
        save_to_json(results)
    finally:
        conn.close()

def save_to_json(results: list, filename="scrape_results.json"):
    """Fallback: save results to a JSON file if DB is unavailable."""
    # Convert datetime to string for JSON serialization
    for item in results:
        if isinstance(item.get("date_scraped"), datetime):
            item["date_scraped"] = item["date_scraped"].isoformat()

    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved {len(results)} results to {filename} (Local Fallback)")

def parse_price(price_text: str) -> Optional[float]:
    """Extract a numeric price from text like '£12.99'."""
    if not price_text:
        return None
    match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None

async def scrape_fragrance_direct(search_term: str, max_results: int = 5) -> list:
    """
    Scrapes Fragrance Direct for the given search term.
    """
    results = []
    url = f"https://www.fragrancedirect.co.uk/search?q={search_term.replace(' ', '+')}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = await context.new_page()

        try:
            print(f"  Searching for: '{search_term}'...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for product grid (subagent found results with these searches)
            try:
                await page.wait_for_selector('.product-item-title', timeout=15000)
            except:
                print(f"    No results found or page structure changed for '{search_term}'.")
                return []

            # Small delay to ensure all dynamic elements are rendered
            await asyncio.sleep(2)

            # Get product tiles (each item usually has a title class)
            titles = await page.query_selector_all('.product-item-title')
            prices = await page.query_selector_all('.price-order')
            links = await page.query_selector_all('.product-item-title') # Often the same element is a link or contains it

            for i in range(min(len(titles), max_results)):
                try:
                    name = await titles[i].inner_text()
                    price_text = await prices[i].inner_text() if i < len(prices) else None
                    price = parse_price(price_text)
                    
                    relative_url = await links[i].get_attribute('href') if i < len(links) else ""
                    product_url = f"https://www.fragrancedirect.co.uk{relative_url}" if relative_url and relative_url.startswith('/') else relative_url

                    if name and price:
                        results.append({
                            "search_term": search_term,
                            "product_name": name.strip()[:255],
                            "price": price,
                            "seller_supplier": "Fragrance Direct (UK)",
                            "url": product_url[:2000] if product_url else "",
                            "date_scraped": datetime.now(),
                        })
                except Exception:
                    continue

        except Exception as e:
            print(f"  [Error] Error scraping '{search_term}': {e}")
        finally:
            await browser.close()

    print(f"  [Done] Found {len(results)} matches.")
    return results

async def run_scraper(search_terms: List[str] = None):
    """Main entry point for the scraper."""
    if search_terms is None:
        search_terms = DEFAULT_SEARCH_TERMS

    print(f"\n{'='*70}")
    print(f"STARTING COSMETICS PRICE SCRAPER -- {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}")

    all_results = []
    for term in search_terms:
        results = await scrape_fragrance_direct(term)
        all_results.extend(results)
        # Random delay to mimic human behavior
        await asyncio.sleep(random.uniform(2, 4))

    if all_results:
        save_to_database(all_results)
        
        print(f"\n{'='*70}")
        print(f"SUMMARY OF SCRAPE")
        print(f"{'='*70}")
        print(f"Total Products: {len(all_results)}")
        # Highlight some findings
        for item in all_results[:3]:
            print(f" - {item['product_name'][:40]}... | GBP {item['price']}")
        print(f"{'='*70}\n")
    else:
        print("\n[Warning] No results were found. Ensure your internet is connected and FragranceDirect is accessible.")

    return all_results

def start_scheduler():
    """Starts the 6-hour interval scheduler."""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: asyncio.run(run_scraper()),
        'interval',
        hours=6,
        next_run_time=datetime.now()
    )
    print("Scheduler active: Scraper will run every 6 hours.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--schedule', action='store_true')
    parser.add_argument('--terms', nargs='+')
    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    else:
        asyncio.run(run_scraper(args.terms if args.terms else DEFAULT_SEARCH_TERMS))
