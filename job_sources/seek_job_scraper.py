# job_sources/seek_job_scraper.py
import time
import random
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from DrissionPage import Chromium, ChromiumOptions
from pygments.lexers import automation
from urllib.parse import urljoin
from config.settings import Config
import logging
import os

logger = logging.getLogger(__name__)

class SeekJobScraper:
    def __init__(self, base_url=None):
        self.browser = None
        self.init_drission()
        self.max_jobs_for_description = Config.MAX_JOBS_FOR_DESCRIPTION
        self.max_jobs_to_scrape = Config.MAX_JOBS_TO_SCRAPE
        self.base_url = base_url or os.getenv("SEEK_JOB_URL")

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
            .set_user_agent("Mozilla/5.0...")
        if config.RUNNING_IN_DOCKER:
            options.no_sandbox(True)
            options.disable_gpu(True)

        self.browser = Chromium(options)

    def scrape_jobs(self):
        """Main method to scrape Seek job listings"""
        if not self.validate_url(self.base_url):
            logger.error(f"Invalid Seek URL: {self.base_url}")
            return []
        try:
            tab = self.browser.latest_tab
            tab.get(self.base_url)
            self.random_delay(3, 5)
            all_jobs = []
            page_count = 1
            while True:
                logger.info(f"Processing page {page_count}")

                # Wait for jobs to load
                # tab.wait.ele_loaded('article[data-automation="job-card"]', timeout=30)
                self.random_delay(1, 2)

                # Parse and extract jobs
                soup = BeautifulSoup(tab.html, 'html.parser')

                jobs = self._extract_jobs(soup)
                if not jobs:
                    logger.info("No more jobs found on page")
                    break
                all_jobs.extend(jobs)
                # Check job limits
                if len(all_jobs) >= self.max_jobs_to_scrape:
                    logger.info(f"Reached max jobs limit ({self.max_jobs_to_scrape})")
                    break
                # Pagination handling
                if not self._handle_pagination(tab):
                    logger.info("No more pages available")
                    break
                page_count += 1
                self.random_delay(2, 4)
            return all_jobs[:self.max_jobs_to_scrape]
        except Exception as e:
            logger.error(f"Seek scraping failed: {str(e)}")
            return []

    def _handle_pagination(self, tab):
        """Handle pagination by clicking the Next button"""
        try:
            # Find the pagination navigation element
            pagination_nav = tab.ele('nav[aria-label="Pagination of results"]', timeout=10)

            # Find active Next button (not disabled)
            next_btn = pagination_nav.ele(
                'xpath:.//a[contains(@rel, "next") and '
                'not(contains(@class, "disabled")) and '
                '(.//span[contains(text(), "Next")] or @aria-label="Next")]'
            )

            if next_btn:
                logger.debug("Clicking Next page button")
                next_btn.click()
                # Wait for new page to load
                tab.wait.ele_loaded('article[data-automation="job-card"]', timeout=20)
                return True
        except Exception as e:
            logger.debug(f"Could not find pagination controls: {str(e)}")
        return False

    def _extract_jobs(self, soup):
        """Extract job listings from current page"""
        job_cards = soup.select('article[data-testid="job-card"]')
        # print(job_cards)
        jobs = []
        for card in job_cards:
            if len(jobs) >= self.max_jobs_to_scrape:
                break
            job = {
                'title': self._safe_extract(card, '[data-automation="jobTitle"]', 'text'),
                'company': self._safe_extract(card, '[data-automation="jobCompany"]', 'text'),
                'location': self._clean_location(card),
                'salary': self._safe_extract(card, '[data-automation="jobSalary"]', 'text'),
                'posted_date': self._safe_extract(card, '[data-automation="jobListingDate"]', 'text'),
                'job_url': self._get_job_url(card),
                'description': self._safe_extract(card, '[data-testid="job-card-teaser"]', 'text'),
                'work_type': self._safe_extract(card, '[data-automation="jobWorkType"]', 'text'),
                'classification': self._safe_extract(card, '[data-automation="jobClassification"]', 'text')
            }
            if len(jobs) < self.max_jobs_for_description:
                job['full_description'] = self._get_full_description(job['job_url'])
            else:
                job['full_description'] = ""
            jobs.append(job)
        return jobs

    from urllib.parse import urljoin

    def _get_job_url(self, card):
        """Extract and validate job URL from card"""
        try:
            # Find the anchor element using multiple attributes
            link_element = card.select_one(
                'a[data-automation="jobTitle"][href], '
                'a[data-testid="job-card-title"][href]'
            )

            if not link_element:
                logger.debug("No job title link element found")
                return ""

            raw_href = link_element.get('href', '').strip()
            if not raw_href:
                logger.debug("Found job title element but no href attribute")
                return ""

            # Clean the URL parameters
            clean_path = raw_href.split('?')[0].split('#')[0]

            # Construct full URL using urljoin to handle relative/absolute paths
            full_url = urljoin("https://www.seek.com.au", clean_path)

            # Validate the URL structure
            if "/job/" not in full_url:
                logger.warning(f"Unexpected job URL format: {full_url}")
                return ""

            return full_url

        except Exception as e:
            logger.error(f"Error extracting job URL: {str(e)}")
            return ""

    def _clean_location(self, card):
        """Combine location elements"""
        locations = card.select('[data-type="location"]')
        return ', '.join([loc.get_text(strip=True) for loc in locations if loc])

    def _get_full_description(self, job_url):
        """Fetch full description using BeautifulSoup parsing"""
        if not job_url:
            return ""
        new_tab = None
        try:
            # Create and switch to new tab
            new_tab = self.browser.new_tab()
            new_tab.get(job_url)

            # Wait for page to fully load
            new_tab.wait.doc_loaded()
            self.random_delay(1.5, 2.5)  # Allow JS execution
            # Get page HTML and parse with BeautifulSoup
            page_html = new_tab.html
            soup = BeautifulSoup(page_html, 'html.parser')

            # Find description container with multiple fallbacks
            desc_container = soup.find('div', {'data-automation': 'jobAdDetails'}) or \
                             soup.find('div', class_='yvsb870') or \
                             soup.find('div', class_=lambda x: x and 'description' in x.lower())
            if desc_container:
                # Clean up unwanted elements
                for element in desc_container(['script', 'style', 'button', 'footer']):
                    element.decompose()

                desc = desc_container.get_text(separator='\n', strip=True)
            else:
                logger.warning(f"Description container not found in HTML")
                desc = ""
                # For debugging: Save HTML to file
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(page_html)

            return desc
        except Exception as e:
            logger.error(f"Description extraction failed: {str(e)}")
            return ""

    def _go_to_next_page(self, tab):
        """Click next page button if available"""
        try:
            next_btn = tab.ele('a[data-automation="page-next"]', timeout=10)
            if next_btn:
                next_btn.click()
                return True
        except Exception as e:
            logger.debug("No next page button found")
        return False

    def _safe_extract(self, element, selector, attr='text'):
        """Safely extract data from element"""
        elem = element.select_one(selector)
        if not elem:
            return ""

        if attr == 'text':
            return elem.get_text(strip=True)
        return elem.get(attr, "")

    def validate_url(self, url):
        """Validate Seek job search URL"""
        parsed = urlparse(url)
        return parsed.netloc == "www.seek.com.au"

    def random_delay(self, min_sec, max_sec):
        """Random delay between actions"""
        time.sleep(random.uniform(min_sec, max_sec))

    def __del__(self):
        if self.browser:
            self.browser.quit()
