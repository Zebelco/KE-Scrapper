import json
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://kemu.edu.pk"
START_URL = "https://kemu.edu.pk/datesheets/"

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

        # Program headings
        if tag.name in ["h2", "h3", "h4"]:
            current_program = tag.get_text(" ", strip=True)
            continue

        href = tag.get("href")

        if not href:
            continue

        href = urljoin(BASE_URL, href)

        # Keep only date sheet pages
        if "/datesheets/" not in href:
            continue

        # Skip index page
        if href.rstrip("/") == START_URL.rstrip("/"):
            continue

        if href in seen:
            continue

        seen.add(href)

        title = tag.get_text(" ", strip=True)

        # Ignore empty links
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


if __name__ == "__main__":

    data = scrape()

    with open("kemu_datesheets.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print()
    print("=" * 40)
    print(f"Saved {len(data)} date sheets")
    print("=" * 40)