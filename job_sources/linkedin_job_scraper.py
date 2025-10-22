import time
import random
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from DrissionPage import Chromium, ChromiumOptions
from config.settings import Config
import logging
import os

logger = logging.getLogger(__name__)

class LinkedInJobScraper:
    def __init__(self, base_url=None):
        self.browser = None
        self.init_drission()
        self.max_jobs_for_description = Config.MAX_JOBS_FOR_DESCRIPTION
        self.max_jobs_to_scrape = Config.MAX_JOBS_TO_SCRAPE
        self.base_url = base_url or os.getenv("LINKEDIN_JOB_URL")

    def init_drission(self):
        """Initialize DrissionPage browser"""
        options = ChromiumOptions()
        # Get values from Config
        config = Config()

        options.auto_port(True) \
            .headless(config.HEADLESS) \
            .no_imgs(True) \
            .mute(True) \
            .incognito(True) \
            .set_paths(browser_path=config.CHROMIUM_PATH or config.CHROME_PATH) \
            .set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        if config.RUNNING_IN_DOCKER:
            options.set_argument('--no-sandbox')
            options.set_argument('--disable-gpu')

        self.browser = Chromium(options)

    def scrape_job_page(self, url):
        """Main method to scrape job details from LinkedIn URL"""
        if not self.validate_url(url):
            logger.error(f"Invalid LinkedIn URL: {url}")
            return None

        try:
            # logger.debug(f"Navigate to LinkedIn URL: {url}")
            jobs = self.browser_scrape(url)
            if jobs is None or len(jobs) == 0:
                logger.warning(f"No jobs parsed from LinkedIn page at {url}")  # [LOG]
            else:
                logger.info(f"Parsed {len(jobs)} jobs from LinkedIn page at {url}")  # [LOG]
            return jobs
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
            return None

    def browser_scrape(self, url):
        """Browser-based scraping using DrissionPage"""
        try:
            logger.info(f"Opening LinkedIn search page: {url}")
            tab = self.browser.latest_tab
            tab.get(url)
            self.random_delay(3, 5)

            # Handle LinkedIn login wall
            logger.debug("Handling login wall if present")
            self.handle_login_wall(tab)

            # Handle cookie consent
            logger.debug("Handling cookie consent if present")
            self.accept_cookies(tab)

            # Wait for main content using multiple possible selectors
            logger.info("Waiting for job search results to load")
            try:
                tab.ele('.jobs-search-results', timeout=20)
            except Exception as e:
                logger.error(f"Error waiting for job search results: {str(e)}")
                tab.screenshot('jobs_search_results_error.png')
                raise

            # Scroll to load all available jobs
            logger.info("Loading all job listings by scrolling")
            self.load_all_jobs(tab)

            soup = BeautifulSoup(tab.html, 'html.parser')
            logger.info("Successfully loaded page and parsed HTML")

            job_listings = self.extract_job_listings(soup)
            if not job_listings:
                logger.warning("No job listings found on the page")
            else:
                logger.info(f"Found {len(job_listings)} job listings after HTML parse")
            return job_listings

        except Exception as e:
            logger.error(f"Browser scraping failed: {str(e)}")
            return None

    def load_all_jobs(self, tab):
        """Scroll page until 'See more jobs' button appears and load all listings"""
        max_attempts = 2
        attempts = 0
        previous_max_row = 0

        while attempts < max_attempts:
            # Scroll to bottom of page
            tab.actions.scroll(100000,10)
            self.random_delay(1, 2)

            # Check how many job elements are present so far
            job_cards = tab.eles('@class=base-card relative w-full hover:no-underline '
                                 'focus:no-underline base-card--link base-search-card '
                                 'base-search-card--link job-search-card')
            job_count = len(job_cards)
            # If we've loaded enough job cards, we can break early
            if job_count >= self.max_jobs_to_scrape:
                logger.debug(f"Loaded enough job cards: {job_count}. Stopping early...")
                break

            # Check current maximum data-row value
            current_rows = [int(ele.attr('data-row')) for ele in tab.eles('@class=base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card')]
            current_max = max(current_rows) if current_rows else 0

            logger.debug(f"Current max data-row: {current_max}, Previous: {previous_max_row}")
            # Check if new jobs were loaded
            if current_max > previous_max_row:
                previous_max_row = current_max
                attempts = 0
            else:
                attempts += 1

            # Check for "See more jobs" button
            see_more_button = tab.ele('@@tag()=button@@text()=See more jobs')

            if see_more_button:
                logger.debug("Found 'See more jobs' button, clicking...")
                see_more_button.click()
                self.random_delay(3, 5)
                attempts = 0  # Reset counter after successful click

            # Exit if no progress
            if attempts >= max_attempts:
                logger.debug("No new jobs loaded after multiple attempts. Stopping...")
                break

            self.random_delay(1, 2)

    def handle_login_wall(self, tab):
        """Attempt to bypass LinkedIn login prompts by simulating a click"""
        try:
            logger.debug("Simulating a click to dismiss the login popup")
            tab.actions.click()
            self.random_delay(2, 4)
        except Exception as e:
            logger.warning(f"Could not simulate click to dismiss login popup: {str(e)}")
            try:
                # Fallback to body click
                tab.actions.click()
                self.random_delay(2, 4)
            except Exception as e:
                logger.warning(f"Could not simulate click: {str(e)}")

    def accept_cookies(self, tab):
        """Accept LinkedIn cookie consent if present"""
        try:
            logger.debug("Attempting to accept cookies")
            cookie_button = tab.ele("button[data-control-name='ga-cookie.consent.accept.v3']", timeout=5)
            if cookie_button:
                cookie_button.click()
                self.random_delay(1, 2)
        except Exception as e:
            logger.debug("No cookie consent button found or could not click it: {str(e)}")

    def extract_job_listings(self, soup):
        """Extract job listings from the search results page"""
        job_listings = []
        job_cards = soup.select("div.base-search-card")

        logger.info(f"Found {len(job_cards)} job cards in the HTML")

        # Limit how many total job cards to process
        max_listings = self.max_jobs_to_scrape

        # Limit number of jobs to process descriptions for
        max_jobs_for_description = self.max_jobs_for_description

        processed_cards = 0  # track total processed job listings
        processed_descriptions = 0  # track how many have descriptions

        for job_card in job_cards:
            processed_cards += 1
            if processed_cards > max_listings:
                # Don't parse more than the user-defined limit
                break
            job_url = job_card.select_one("a.base-card__full-link")
            job_url = job_url["href"] if job_url else ""
            fetch_desc = (processed_descriptions < max_jobs_for_description)
            if fetch_desc:
                processed_descriptions += 1
                desc = self.get_job_description(job_url)
            else:
                desc = ""
            # Improved company extraction with multiple fallbacks
            company = ""
            company_selectors = [
                "h4.base-search-card__subtitle a",
                "h4.base-search-card__subtitle",
                "a.hidden-nested-link",
                "span.job-search-card__company-name"
            ]
            for selector in company_selectors:
                company_element = job_card.select_one(selector)
                if company_element:
                    company = company_element.get_text(strip=True)
                    if company:
                        break
            if not company:
                logger.warning(f"Could not extract company name for job: {job_url}")
                # Optionally log the HTML for debugging:
                # logger.debug(f"Job card HTML: {job_card.prettify()}")
                company = "Unknown Company"
            job = {
                "title": job_card.select_one("h3.base-search-card__title").get_text(strip=True)
                if job_card.select_one("h3.base-search-card__title") else "",
                "company": company,
                "location": job_card.select_one("span.job-search-card__location").get_text(strip=True)
                if job_card.select_one("span.job-search-card__location") else "",
                "posted_date": job_card.select_one("time.job-search-card__listdate").get_text(strip=True)
                if job_card.select_one("time.job-search-card__listdate") else "",
                "job_url": job_url,
                "description": desc
            }
            job_listings.append(job)

        logger.info(f"Extracted {len(job_listings)} job listings")
        return job_listings

    def get_job_description(self, job_url):
        """Fetch job description from individual job page"""
        if not job_url:
            return ""
        try:
            # Open job page in new tab
            logger.info(f"Opening LinkedIn job page for description: {job_url}")
            new_tab = self.browser.new_tab()
            new_tab.get(job_url)
            self.random_delay(3, 5)
            # Handle potential popups in new tab
            self.handle_login_wall(new_tab)
            # self.accept_cookies(new_tab)

            # Wait for description content
            try:
                logger.debug(f"Extracting job description")
                description_element = new_tab.ele('@@tag()=div@@class=description__text description__text--rich')
                description = description_element.text.strip() if description_element else ""
            except Exception as e:
                logger.warning(f"Could not extract description: {str(e)}")
                description = ""

            # Close the tab and return to main window
            # logger.debug(f"Extracted job description {description}")
            new_tab.close()
            return description

        except Exception as e:
            logger.error(f"Failed to get description from {job_url}: {str(e)}")
            return ""

    def validate_url(self, url):
        """Ensure we're only scraping LinkedIn job search URLs"""
        parsed = urlparse(url)
        return parsed.netloc in ["www.linkedin.com", "linkedin.com"] and "/jobs/search/" in url

    def random_delay(self, min_sec, max_sec):
        """Random delay to mimic human behavior"""
        time.sleep(random.uniform(min_sec, max_sec))

    def __del__(self):
        if self.browser:
            self.browser.quit()
