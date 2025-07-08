import pandas as pd
import sys
import os
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright
import re

# ---------- Settings ----------
IT_KEYWORDS = [
    "data", "developer", "software", "engineer", "it", "cloud", "infrastructure",
    "network", "devops", "cyber", "security", "ai", "ml", "machine learning",
    "backend", "frontend", "fullstack", "qa", "support", "tech", "analyst", "sql"
]

HEADERS = {'User-Agent': 'Mozilla/5.0'}

# ---------- Helpers ----------
def is_it_job(title):
    return any(re.search(rf"\b{kw}\b", title, re.IGNORECASE) for kw in IT_KEYWORDS)

def scrape_static(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        tags = soup.find_all(['a', 'li', 'span', 'p', 'h2', 'h3'])
        jobs = {
            tag.get_text(strip=True)
            for tag in tags
            if 5 < len(tag.get_text(strip=True)) < 100 and is_it_job(tag.get_text(strip=True))
        }
        return list(jobs)
    except Exception as e:
        print(f"[STATIC] Error scraping {url}: {e}")
        return []

def scrape_dynamic(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()

            tags = soup.find_all(['a', 'li', 'span', 'p', 'h2', 'h3'])
            jobs = {
                tag.get_text(strip=True)
                for tag in tags
                if 5 < len(tag.get_text(strip=True)) < 100 and is_it_job(tag.get_text(strip=True))
            }
            return list(jobs)
    except Exception as e:
        print(f"[DYNAMIC] Error scraping {url}: {e}")
        return []

# ---------- Main scraper ----------
def main(batch_file):
    print(f"\n📦 Processing batch: {batch_file}")
    results = []
    df = pd.read_excel(batch_file)

    for _, row in df.iterrows():
        company = row.get("Company")
        url = row.get("Website")

        if not url or pd.isna(url):
            continue

        print(f"🔎 Scraping {company}: {url}")
        jobs = scrape_static(url)
        if not jobs:
            jobs = scrape_dynamic(url)

        for job in set(jobs):
            results.append({
                "Company": company,
                "Job Title": job,
                "URL": url,
                "Batch": os.path.basename(batch_file),
                "Scrape Time": datetime.now().isoformat()
            })

    # Always write an output file, even if empty
    output_file = f"results_{os.path.basename(batch_file).replace('.xlsx', '.csv')}"
    if results:
        pd.DataFrame(results).to_csv(output_file, index=False)
    else:
        pd.DataFrame(columns=["Company", "Job Title", "URL", "Batch", "Scrape Time"]).to_csv(output_file, index=False)

    print(f"✅ Done: {output_file}")

# ---------- Entry Point ----------
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scrape.py batches/career_sites_batch_01.xlsx")
        sys.exit(1)

    main(sys.argv[1])
