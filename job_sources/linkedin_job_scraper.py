import time
import random
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from DrissionPage import Chromium, ChromiumOptions
from config.settings import Config
from job_sources.linkedin_cookie_manager import get_cookie_manager
import logging
import os

logger = logging.getLogger(__name__)

class LinkedInJobScraper:
    def __init__(self, base_url=None):
        self.browser = None
        self.cookie_manager = get_cookie_manager()
        self.has_valid_session = False
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
            .no_imgs(False) \
            .mute(True) \
            .set_paths(browser_path=config.CHROMIUM_PATH or config.CHROME_PATH) \
            .set_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        # Anti-detection flags to avoid LinkedIn blocking
        options.set_argument('--disable-blink-features=AutomationControlled')
        options.set_argument('--disable-infobars')
        options.set_argument('--disable-extensions')
        options.set_argument('--disable-dev-shm-usage')
        options.set_argument('--window-size=1920,1080')

        if config.RUNNING_IN_DOCKER:
            options.set_argument('--no-sandbox')
            options.set_argument('--disable-gpu')
            options.set_argument('--single-process')

        self.browser = Chromium(options)

        # Load saved cookies if available
        self._load_cookies()

    def _load_cookies(self):
        """Load saved LinkedIn cookies into the browser session."""
        if not self.cookie_manager.has_cookies():
            logger.info("No saved LinkedIn cookies found. Will use anonymous scraping.")
            logger.info("Tip: Run 'python -m job_sources.linkedin_login' to enable authenticated access.")
            return False

        cookies = self.cookie_manager.load_cookies()
        if not cookies:
            logger.warning("Failed to load cookies from file.")
            return False

        try:
            # First, navigate to LinkedIn to set the cookie domain
            tab = self.browser.latest_tab
            tab.get("https://www.linkedin.com")
            self.random_delay(1, 2)

            # Apply each cookie
            for cookie in cookies:
                try:
                    tab.set.cookies(cookie)
                except Exception as e:
                    logger.debug(f"Could not set cookie {cookie.get('name', 'unknown')}: {e}")

            logger.info(f"Applied {len(cookies)} LinkedIn cookies to browser session")
            self.has_valid_session = True
            return True

        except Exception as e:
            logger.error(f"Failed to apply cookies: {e}")
            return False

    def _verify_session(self, tab) -> bool:
        """Verify if the current session is authenticated."""
        try:
            # Check for login wall indicators
            login_indicators = [
                'authwall',
                'login',
                'sign-in'
            ]
            current_url = tab.url.lower()

            for indicator in login_indicators:
                if indicator in current_url:
                    return False

            # Check for authenticated content indicators
            try:
                # Look for job search results (authenticated users see more)
                if tab.ele('.jobs-search-results', timeout=5):
                    return True
            except:
                pass

            return self.has_valid_session
        except:
            return False

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
            session_type = "authenticated" if self.has_valid_session else "anonymous"
            logger.info(f"Opening LinkedIn search page ({session_type}): {url}")

            tab = self.browser.latest_tab
            tab.get(url)
            self.random_delay(3, 5)

            # Handle cookie consent first
            logger.debug("Handling cookie consent if present")
            self.accept_cookies(tab)

            # Check if we need to handle login wall
            if not self.has_valid_session:
                logger.debug("Handling login wall if present (no saved session)")
                self.handle_login_wall(tab)
            else:
                # Verify our session is still valid
                if not self._verify_session(tab):
                    logger.warning("Saved session appears invalid. Falling back to anonymous mode.")
                    self.has_valid_session = False
                    self.handle_login_wall(tab)

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
        previous_job_count = 0

        while attempts < max_attempts:
            # Scroll to bottom of page
            tab.actions.scroll(100000, 10)
            self.random_delay(1, 2)

            # Check how many job elements are present
            # Try authenticated view first (data-job-id)
            job_cards = tab.eles('@data-job-id')

            # Try anonymous view with new structure
            if not job_cards:
                job_cards = tab.eles('@data-chameleon-result-urn')

            # Fallback to old selector
            if not job_cards:
                job_cards = tab.eles('@class=base-card relative w-full hover:no-underline '
                                     'focus:no-underline base-card--link base-search-card '
                                     'base-search-card--link job-search-card')

            job_count = len(job_cards)
            logger.debug(f"Current job count: {job_count}, Previous: {previous_job_count}")

            # If we've loaded enough job cards, we can break early
            if job_count >= self.max_jobs_to_scrape:
                logger.debug(f"Loaded enough job cards: {job_count}. Stopping early...")
                break

            # Check if new jobs were loaded
            if job_count > previous_job_count:
                previous_job_count = job_count
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
        """Extract job listings from the search results page.

        Supports multiple LinkedIn HTML structures:
        1. Job Search view (authenticated): div[data-job-id] with artdeco-entity-lockup structure
        2. My Jobs/Saved Jobs view: div[data-chameleon-result-urn] with obfuscated classes
        3. Public/anonymous view (fallback): div.base-search-card
        """
        job_listings = []

        # Strategy 1: Authenticated view - job cards with data-job-id attribute
        job_cards = soup.select("div[data-job-id]")
        selector_used = "authenticated (data-job-id)"

        # Strategy 2: Anonymous view with new structure
        if not job_cards:
            job_cards = soup.select("div[data-chameleon-result-urn]")
            selector_used = "anonymous-new (data-chameleon-result-urn)"

        # Strategy 3: Old anonymous structure (fallback)
        if not job_cards:
            job_cards = soup.select("div.base-search-card")
            selector_used = "anonymous-old (base-search-card)"

        logger.info(f"Using {selector_used} selector: Found {len(job_cards)} job cards")

        # Limit how many total job cards to process
        max_listings = self.max_jobs_to_scrape
        max_jobs_for_description = self.max_jobs_for_description

        processed_cards = 0
        processed_descriptions = 0

        for job_card in job_cards:
            processed_cards += 1
            if processed_cards > max_listings:
                break

            # Extract job URL - multiple strategies
            job_url = ""
            job_link = None

            # Try authenticated view selector first
            job_link = job_card.select_one("a.job-card-container__link[href*='/jobs/view/']")
            if not job_link:
                # Try generic /jobs/view/ link
                job_link = job_card.select_one("a[href*='/jobs/view/']")
            if not job_link:
                # Fallback to old structure
                job_link = job_card.select_one("a.base-card__full-link")

            if job_link:
                job_url = job_link.get("href", "")

            # Fetch description for limited number of jobs
            fetch_desc = (processed_descriptions < max_jobs_for_description)
            desc = ""
            company_from_detail = ""
            if fetch_desc and job_url:
                processed_descriptions += 1
                desc, company_from_detail = self.get_job_description(job_url)

            # Extract title - multiple strategies
            title = ""
            if job_link:
                # Authenticated view: title in span[aria-hidden] > strong
                title_strong = job_link.select_one("span[aria-hidden='true'] strong")
                if title_strong:
                    title = title_strong.get_text(strip=True)
                else:
                    # Try span[aria-hidden] directly
                    title_span = job_link.select_one("span[aria-hidden='true']")
                    if title_span:
                        title = title_span.get_text(strip=True)
                    else:
                        # Get text from link directly
                        title = job_link.get_text(strip=True)
            # Fallback to old structure
            if not title:
                title_elem = job_card.select_one("h3.base-search-card__title")
                title = title_elem.get_text(strip=True) if title_elem else ""

            # Extract company - multiple strategies
            company = ""

            # Authenticated view: company in artdeco-entity-lockup__subtitle
            subtitle_elem = job_card.select_one(".artdeco-entity-lockup__subtitle span")
            if subtitle_elem:
                company = subtitle_elem.get_text(strip=True)

            # Try company tracking link
            if not company:
                company_link = job_card.select_one("a[data-tracking-control-name*='company']")
                if company_link:
                    company = company_link.get_text(strip=True)

            # Try /company/ link
            if not company:
                company_link = job_card.select_one("a[href*='/company/']")
                if company_link:
                    company = company_link.get_text(strip=True)

            # Fallback to old structure selectors
            if not company:
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

            # Fallback to company from detail page
            if not company and company_from_detail:
                company = company_from_detail
                logger.debug(f"Using company from detail page: {company}")

            if not company:
                logger.warning(f"Could not extract company name for job: {job_url}")
                company = "Unknown Company"

            # Extract location - multiple strategies
            location = ""

            # Authenticated view: location in artdeco-entity-lockup__caption
            caption_elem = job_card.select_one(".artdeco-entity-lockup__caption li span")
            if caption_elem:
                location = caption_elem.get_text(strip=True)

            # Try metadata wrapper
            if not location:
                metadata_elem = job_card.select_one(".job-card-container__metadata-wrapper li span")
                if metadata_elem:
                    location = metadata_elem.get_text(strip=True)

            # Try span with location class
            if not location:
                location_elem = job_card.select_one("span[class*='location']")
                if location_elem:
                    location = location_elem.get_text(strip=True)

            # Look for location patterns in all spans
            if not location:
                all_spans = job_card.find_all("span")
                for span in all_spans:
                    text = span.get_text(strip=True)
                    if text and any(loc in text.lower() for loc in ['australia', 'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide', 'remote', 'hybrid', 'on-site', 'nsw', 'vic', 'qld', 'wa', 'sa']):
                        location = text
                        break

            # Fallback to old structure
            if not location:
                location_elem = job_card.select_one("span.job-search-card__location")
                location = location_elem.get_text(strip=True) if location_elem else ""

            # Extract posted date
            posted_date = ""
            time_elem = job_card.select_one("time")
            if time_elem:
                posted_date = time_elem.get_text(strip=True)
            if not posted_date:
                time_elem = job_card.select_one("time.job-search-card__listdate")
                posted_date = time_elem.get_text(strip=True) if time_elem else ""

            # Only add if we have at least a title or URL
            if title or job_url:
                job = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "posted_date": posted_date,
                    "job_url": job_url,
                    "description": desc
                }
                job_listings.append(job)
                logger.debug(f"Extracted job: {title} at {company} ({location})")
            else:
                logger.warning(f"Skipping job card with no title or URL")

        logger.info(f"Extracted {len(job_listings)} job listings")
        return job_listings

    def get_job_description(self, job_url):
        """Fetch job description and company name from individual job page"""
        if not job_url:
            return "", ""
        try:
            # Convert relative URLs to absolute
            if job_url.startswith('/'):
                job_url = f"https://www.linkedin.com{job_url}"

            # Open job page in new tab
            logger.info(f"Opening LinkedIn job page for details: {job_url}")
            new_tab = self.browser.new_tab()
            new_tab.get(job_url)
            self.random_delay(3, 5)
            # Handle potential popups in new tab
            self.handle_login_wall(new_tab)
            
            # Extract company name from detail page
            company = ""
            company_selectors = [
                '@@tag()=div@@class=job-details-jobs-unified-top-card__company-name',
                '@@tag()=a@@class=topcard__org-name-link',
                '@@tag()=span@@class=topcard__flavor--black',
                '@@tag()=a@@data-tracking-control-name=public_jobs_topcard-org-name'
            ]
            for selector in company_selectors:
                try:
                    company_element = new_tab.ele(selector, timeout=2)
                    if company_element:
                        company = company_element.text.strip()
                        if company:
                            logger.debug(f"Extracted company from detail page: {company}")
                            break
                except:
                    continue

            # Wait for description content
            description = ""
            try:
                logger.debug(f"Extracting job description")
                description_element = new_tab.ele('@@tag()=div@@class=description__text description__text--rich', timeout=5)
                description = description_element.text.strip() if description_element else ""
            except Exception as e:
                logger.warning(f"Could not extract description: {str(e)}")

            # Close the tab and return to main window
            new_tab.close()
            return description, company

        except Exception as e:
            logger.error(f"Failed to get details from {job_url}: {str(e)}")
            return "", ""

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
