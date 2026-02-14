"""jobs/services/scraper.py - Ekstrakcja tekstu oferty pracy z URL."""

import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class JobScraper:
    """Pobiera i ekstraktuje tekst oferty pracy z URL."""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    TIMEOUT = 15

    @classmethod
    def scrape_url(cls, url):
        """Pobiera tekst oferty pracy z URL.

        Returns:
            dict z kluczami: 'text' (str), 'title' (str), 'error' (str|None)
        """
        try:
            response = requests.get(url, headers=cls.HEADERS, timeout=cls.TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()

            title = ''
            title_tag = soup.find('h1')
            if title_tag:
                title = title_tag.get_text(strip=True)

            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = '\n'.join(lines)

            if len(clean_text) < 50:
                return {'text': '', 'title': '', 'error': 'Could not extract meaningful text from the page.'}

            return {
                'text': clean_text[:10000],
                'title': title[:255],
                'error': None,
            }

        except requests.RequestException as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return {'text': '', 'title': '', 'error': str(e)}
