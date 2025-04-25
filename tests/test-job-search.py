import csv
from jobspy import scrape_jobs

jobs = scrape_jobs(
    # site_name=["indeed", "linkedin", "zip_recruiter", "glassdoor", "google", "bayt", "naukri"],
    site_name=["indeed", "glassdoor", "google"],
    search_term='AI IT (manager OR head OR director) software',
    google_search_term="head of IT or IT manager or software engineering manager or AI jobs near Melbourne, VIC since yesterday",
    location="Melbourne, VIC",
    job_type="fulltime",
    results_wanted=20,
    hours_old=168,
    country_indeed='australia',

    # linkedin_fetch_description=True # gets more info such as description, direct job url (slower)
    # proxies=["208.195.175.46:65095", "208.195.175.45:65095", "localhost"],
)
print(f"Found {len(jobs)} jobs")
print(jobs.head())
jobs.to_csv("jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False)  # to_excel