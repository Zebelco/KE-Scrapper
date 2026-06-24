import argparse
import json
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://kemu.edu.pk"
START_URL = "https://kemu.edu.pk/datesheets/"
OUTPUT_FILE = "kemu_datesheets.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_soup(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def extract_year(text):
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else ""


def extract_date(page):
    """
    Try multiple places where WordPress stores the date.
    """
    selectors = [
        "time",
        ".entry-date",
        ".posted-on",
        ".post-date",
        ".entry-meta",
        ".elementor-post-info__item--type-date"
    ]

    for selector in selectors:
        tag = page.select_one(selector)
        if tag:
            text = tag.get_text(" ", strip=True)
            if text:
                return text

    return ""


def extract_pdf(page):
    """
    Return first PDF found on the page.
    """
    for a in page.find_all("a", href=True):
        href = a["href"]

        if href.lower().endswith(".pdf"):
            return urljoin(BASE_URL, href)

    return ""


def scrape():
    soup = get_soup(START_URL)

    results = []
    seen = set()
    current_program = ""

    # Read headings and links in page order
    for tag in soup.find_all(["h2", "h3", "h4", "a"]):
        if tag.name in ["h2", "h3", "h4"]:
            current_program = tag.get_text(" ", strip=True)
            continue

        href = tag.get("href")
        if not href:
            continue

        href = urljoin(BASE_URL, href)

        if "/datesheets/" not in href:
            continue

        if href.rstrip("/") == START_URL.rstrip("/"):
            continue

        if href in seen:
            continue

        seen.add(href)
        title = tag.get_text(" ", strip=True)

        if len(title) < 5:
            continue

        print("Scraping:", title)

        try:
            page = get_soup(href)
            published_date = extract_date(page)
            pdf_url = extract_pdf(page)

            results.append({
                "program": current_program,
                "title": title,
                "exam_year": extract_year(title),
                "published_date": published_date,
                "page_url": href,
                "pdf_url": pdf_url,
                "scraped_at": datetime.utcnow().isoformat()
            })

        except Exception as e:
            print("Failed:", href, e)

    return results


def save_results(results, output_file=OUTPUT_FILE):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


def run_scrape(output_file=OUTPUT_FILE):
    data = scrape()
    save_results(data, output_file)
    print()
    print("=" * 40)
    print(f"Saved {len(data)} date sheets")
    print("=" * 40)


def parse_args():
    parser = argparse.ArgumentParser(description="Schedule KEMU date sheet scraper")
    parser.add_argument("--interval", type=int, default=2,
                        help="Run every N minutes. Defaults to 2 minutes.")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE,
                        help="Output JSON file path.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.interval <= 0:
        run_scrape(args.output)
    else:
        interval_seconds = args.interval * 60
        print(f"Starting scheduled scraper every {args.interval} minute(s). Press Ctrl+C to stop.")
        next_run = datetime.utcnow()

        try:
            while True:
                now = datetime.utcnow()
                if now >= next_run:
                    print(f"\n[{now.isoformat()}] Running scraper...")
                    run_scrape(args.output)
                    next_run = now + timedelta(seconds=interval_seconds)
                sleep_seconds = max(0, (next_run - datetime.utcnow()).total_seconds())
                time.sleep(min(sleep_seconds, 10))
        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")
