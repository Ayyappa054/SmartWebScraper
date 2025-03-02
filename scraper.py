import requests
from bs4 import BeautifulSoup
import urllib.parse
import os
import json
import time
import random
import hashlib
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
    logging.warning("Install cloudscraper for better scraping: pip install cloudscraper")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()]
)

class GeoPoliticalScraper:
    def __init__(self, keyword, trusted_websites):
        self.keyword = keyword
        self.trusted_websites = [urllib.parse.urlparse(site).netloc.lower() for site in trusted_websites]
        self.output_folder = f"{keyword.replace(' ', '_')}_data"
        self.session = self._create_session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        self.data = {"keyword": keyword, "matched_urls": []}
        self._create_folders()

    def _create_session(self):
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://duckduckgo.com/',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }

    def _create_folders(self):
        folders = [self.output_folder, f"{self.output_folder}/images"]
        for folder in folders:
            os.makedirs(folder, exist_ok=True)
            logging.info(f"Created folder: {folder}")

    def _search_duckduckgo(self):
        search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(self.keyword)}"
        logging.info(f"Searching DuckDuckGo: {search_url}")
        try:
            response = self.session.get(search_url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            anchor_tags = list(set(a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('http')))
            logging.info(f"Found {len(anchor_tags)} unique anchor tags")
            return anchor_tags
        except Exception as e:
            logging.error(f"Error searching DuckDuckGo: {e}")
            return []

    def _verify_trusted_urls(self, anchor_tags):
        trusted_urls = set()
        for url in anchor_tags:
            domain = urllib.parse.urlparse(url).netloc.lower()
            if domain in self.trusted_websites:
                trusted_urls.add(url)
                logging.info(f"Matched trusted URL: {url} (Domain: {domain})")
            else:
                logging.debug(f"Skipped non-trusted URL: {url} (Domain: {domain})")
        return list(trusted_urls)

    def _scrape_content(self, url):
        try:
            if HAS_CLOUDSCRAPER:
                scraper = cloudscraper.create_scraper()
                response = scraper.get(url, headers=self._get_headers(), timeout=15)
            else:
                response = self.session.get(url, headers=self._get_headers(), timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract bulk text with headings
            text_elements = []
            for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                text = elem.get_text(strip=True)
                if text and len(text) > 10:
                    if elem.name.startswith('h'):  # Add heading marker
                        text_elements.append(f"{elem.name.upper()}: {text}")
                    else:
                        text_elements.append(text)
            bulk_text = "\n\n".join(text_elements)

            # Extract image URLs
            image_urls = []
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('srcset')
                if src:
                    if 'srcset' in img.attrs:
                        src = src.split(',')[0].split()[0]
                    absolute_url = urllib.parse.urljoin(url, src)
                    image_urls.append(absolute_url)

            logging.info(f"Scraped {len(text_elements)} text elements and {len(image_urls)} images from {url}")
            return bulk_text, image_urls
        except Exception as e:
            logging.error(f"Error scraping content from {url}: {e}")
            return "", []

    def _download_image(self, img_url):
        try:
            img_name = f"{hashlib.md5(img_url.encode()).hexdigest()}{os.path.splitext(urllib.parse.urlparse(img_url).path)[-1] or '.jpg'}"
            img_path = f"{self.output_folder}/images/{img_name}"
            if not os.path.exists(img_path):
                response = self.session.get(img_url, headers=self._get_headers(), stream=True, timeout=10)
                response.raise_for_status()
                with open(img_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                logging.info(f"Downloaded image: {img_path}")
            return img_path
        except Exception as e:
            logging.error(f"Error downloading image {img_url}: {e}")
            return None

    def _save_to_json(self):
        json_path = f"{self.output_folder}/scraped_data.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)
        logging.info(f"Saved data to {json_path}")

    def _create_pdf(self):
        pdf_path = f"{self.output_folder}/content_document.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        y_position = height - 50

        # Add title and timestamp
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, f"Scraped Content for '{self.keyword}'")
        y_position -= 20
        c.setFont("Helvetica", 10)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.drawString(50, y_position, f"Generated on: {timestamp}")
        y_position -= 30

        for entry in self.data["matched_urls"]:
            url = entry["anchor_tag"]
            text = entry["text"]
            images = entry.get("image_paths", [])

            # Add bulk text with headings
            if text:
                if y_position < 100:
                    c.showPage()
                    y_position = height - 50
                c.setFont("Helvetica", 10)
                text_object = c.beginText(50, y_position)
                text_lines = text.split('\n')
                for line in text_lines:
                    if line.strip():
                        if y_position < 50:
                            c.drawText(text_object)
                            c.showPage()
                            y_position = height - 50
                            text_object = c.beginText(50, y_position)
                        if line.startswith(('H1:', 'H2:', 'H3:', 'H4:', 'H5:', 'H6:')):
                            c.setFont("Helvetica-Bold", 12)
                            text_object.setFont("Helvetica-Bold", 12)
                            text_object.textLine(line[3:])  # Remove 'H#:' prefix
                            c.setFont("Helvetica", 10)
                            text_object.setFont("Helvetica", 10)
                        else:
                            text_object.textLine(line[:100])
                        y_position -= 15
                c.drawText(text_object)

            # Add anchor tag
            if y_position < 50:
                c.showPage()
                y_position = height - 50
            c.setFont("Helvetica", 10)
            c.drawString(50, y_position, f"Source URL: {url}")
            y_position -= 30

            # Add images with heading
            if images:
                if y_position < 200:
                    c.showPage()
                    y_position = height - 50
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y_position, "Images")
                y_position -= 20
                for img_path in images:
                    if os.path.exists(img_path):
                        if y_position < 200:
                            c.showPage()
                            y_position = height - 50
                        try:
                            img = ImageReader(img_path)
                            c.drawImage(img, 50, y_position - 150, width=200, height=150, preserveAspectRatio=True)
                            y_position -= 170
                        except Exception as e:
                            logging.error(f"Error adding image {img_path} to PDF: {e}")

            c.showPage()
            y_position = height - 50

        c.save()
        logging.info(f"Created PDF at {pdf_path}")

    def scrape(self):
        logging.info(f"Starting scrape for keyword: {self.keyword}")
        anchor_tags = self._search_duckduckgo()
        time.sleep(random.uniform(2, 3))
        trusted_urls = self._verify_trusted_urls(anchor_tags)

        for url in trusted_urls:
            bulk_text, image_urls = self._scrape_content(url)
            downloaded_paths = [self._download_image(img_url) for img_url in image_urls]
            downloaded_paths = [path for path in downloaded_paths if path]
            self.data["matched_urls"].append({
                "anchor_tag": url,
                "text": bulk_text,
                "image_urls": image_urls,
                "image_paths": downloaded_paths
            })
            time.sleep(random.uniform(1, 3))

        self._save_to_json()
        self._create_pdf()
        logging.info("Scraping complete")

if __name__ == "__main__":
    keyword = "Geo-political Tension"
    trusted_websites = ["https://www.bloomberg.com/asia", "https://www.forbes.com", "https://www.spglobal.com"]
    scraper = GeoPoliticalScraper(keyword=keyword, trusted_websites=trusted_websites)
    scraper.scrape()