import pandas as pd
import sys
import os
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from playwright.sync_api import sync_playwright
import re

IT_KEYWORDS = ["data", "developer", "software", "engineer", "it", "cloud", "sql", "analyst", "qa", "ai", "ml"]

def is_it_job(title):
    return any(re.search(rf"\b{kw}\b", title, re.IGNORECASE) for kw in IT_KEYWORDS)

def scrape_static(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        return [t.get_text(strip=True) for t in soup.find_all(['a', 'li', 'span', 'h2', 'h3', 'p']) if is_it_job(t.get_text(strip=True))]
    except: return []

def scrape_dynamic(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            browser.close()
            return [t.get_text(strip=True) for t in soup.find_all(['a', 'li', 'span', 'h2', 'h3', 'p']) if is_it_job(t.get_text(strip=True))]
    except: return []

def main(batch_file):
    df = pd.read_excel(batch_file)
    results = []
    for _, row in df.iterrows():
        company, url = row['Company'], row['Website']
        jobs = scrape_static(url) or scrape_dynamic(url)
        for job in set(jobs):
            results.append({
                "Company": company,
                "Job Title": job,
                "URL": url,
                "Batch": os.path.basename(batch_file),
                "Scrape Time": datetime.now().isoformat()
            })
    out_df = pd.DataFrame(results)
    out_df.to_csv(f"results_{os.path.basename(batch_file).replace('.xlsx', '.csv')}", index=False)

if __name__ == "__main__":
    main(sys.argv[1])
