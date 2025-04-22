from bs4 import BeautifulSoup
from utils.logger import setup_logger


class ContentCleaner:
    def __init__(self, max_length=15000):
        self.max_length = max_length
        self.logger = setup_logger(__name__)

    def clean_html(self, html_content):
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['header', 'footer', 'nav', 'script', 'style', 'a']):
                element.decompose()

            # Extract text from paragraphs OR fallback to all text
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            else:
                # Handle plain text by splitting lines and preserving natural breaks
                text = '\n'.join(line.strip() for line in soup.get_text().splitlines() if line.strip())

            return text[:self.max_length]

        except Exception as e:
            self.logger.error(f"HTML cleaning failed: {str(e)}")
            return html_content[:self.max_length]
