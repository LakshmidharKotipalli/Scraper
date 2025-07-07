import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tqdm import tqdm
from google.colab import files
import io

# Upload multiple input files
uploaded = files.upload()

# Read and combine all valid input files
dataframes = []
for filename in uploaded.keys():
    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(uploaded[filename]))
    elif filename.endswith(".xlsx"):
        df = pd.read_excel(io.BytesIO(uploaded[filename]))
    else:
        print(f"❌ Unsupported file format: {filename}")
        continue

    if "Company" not in df.columns or "Website" not in df.columns:
        print(f"⚠️ Skipping {filename}: Missing 'Company' or 'Website' column.")
        continue

    df = df[["Company", "Website"]]
    dataframes.append(df)

if not dataframes:
    raise ValueError("No valid files uploaded.")
df = pd.concat(dataframes, ignore_index=True)

# Clean and fix URLs
def format_url(url):
    if pd.isna(url) or url.strip() in ["", "nan", "None"]:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

df["Website"] = df["Website"].apply(format_url)

# Find career page
def find_career_page(base_url):
    try:
        res = requests.get(base_url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"].lower()
            text = link.get_text().lower()
            if any(k in href or k in text for k in ["career", "jobs", "join-us", "opportunities", "work with us"]):
                return urljoin(base_url, link["href"])
        return None
    except Exception as e:
        print(f"❌ Failed to get career page for {base_url}: {e}")
        return None

# Job keyword matching
KEYWORDS = ["data", "analyst", "analytics", "data science", "machine learning", "bi", "business intelligence"]

def is_data_related(title):
    title = title.lower()
    return any(keyword in title for keyword in KEYWORDS)

# Scrape job info
def scrape_jobs_from_portal(company, url):
    headers = {"User-Agent": "Mozilla/5.0"}
    jobs = []
    try:
        res = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        for link in soup.find_all("a", href=True):
            job_title = link.text.strip()
            job_url = link["href"]

            if is_data_related(job_title):
                full_url = job_url if job_url.startswith("http") else urljoin(url, job_url)
                job_posting_date = "N/A"

                parent = link.find_parent()
                if parent:
                    time_tag = parent.find("time")
                    if time_tag and time_tag.get("datetime"):
                        job_posting_date = time_tag["datetime"]
                    elif time_tag:
                        job_posting_date = time_tag.text.strip()
                    else:
                        context = parent.get_text().lower()
                        for tag in ["posted", "date", "listed", "open"]:
                            if tag in context:
                                job_posting_date = context
                                break

                jobs.append({
                    "Company": company,
                    "JobTitle": job_title,
                    "JobLink": full_url,
                    "Posted": job_posting_date,
                    "CareerPage": url
                })

        return jobs
    except Exception as e:
        print(f"❌ Error scraping {company}: {e}")
        return []

# Loop through companies
all_jobs = []
no_job_companies = []

for _, row in tqdm(df.iterrows(), total=len(df)):
    company = row["Company"]
    base_url = row["Website"]

    if pd.isna(base_url):
        continue

    career_page = find_career_page(base_url)
    if career_page:
        jobs = scrape_jobs_from_portal(company, career_page)
        if jobs:
            all_jobs.extend(jobs)
        else:
            no_job_companies.append({"Company": company, "Website": base_url, "CareerPage": career_page})
    else:
        no_job_companies.append({"Company": company, "Website": base_url, "CareerPage": "Not Found"})

# Save to Excel with two sheets
with pd.ExcelWriter("matched_jobs.xlsx", engine="openpyxl") as writer:
    pd.DataFrame(all_jobs).to_excel(writer, index=False, sheet_name="MatchedJobs")
    pd.DataFrame(no_job_companies).to_excel(writer, index=False, sheet_name="NoJobsFound")

files.download("matched_jobs.xlsx")
