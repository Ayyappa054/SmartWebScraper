# SmartWebScraper
A versatile and intelligent web scraper that extracts relevant content from trusted sources based on user-defined keywords. This tool leverages DuckDuckGo search results and integrates requests, BeautifulSoup, and optionally cloudscraper to handle bot protection.

# SmartWebScraper

SmartWebScraper is an advanced web scraping tool that extracts both text and images from trusted websites based on a given keyword. It automates data collection, processes content efficiently, and stores the results in structured formats such as JSON and PDF.

## Features
- **Keyword-Based Scraping**: Extracts text and images related to any given keyword.
- **Trusted Websites Filtering**: Scrapes only from specified trusted domains to ensure data reliability.
- **Automated Search**: Uses DuckDuckGo to find relevant pages.
- **Efficient Web Scraping**: Supports Cloudflare-protected sites (with optional cloudscraper support).
- **Robust Session Handling**: Implements retries and user-agent rotation to avoid request blocks.
- **Data Storage**: Saves extracted data in JSON format and generates a structured PDF report.

## Installation
### Prerequisites
Ensure you have Python 3 installed, then install the required dependencies:
```bash
pip install -r requirements.txt
```
If you want improved Cloudflare bypass support, install:
```bash
pip install cloudscraper
```

## Usage
1. Modify the script to specify your desired keyword and trusted websites.
2. Run the script:
```bash
python scraper.py
```
3. Extracted data will be saved in the `keyword_data` folder as:
   - `scraped_data.json`: Contains structured text and image URLs.
   - `content_document.pdf`: A formatted PDF report with text and images.

## Output
- **JSON File**: Stores extracted text, image URLs, and their local paths.
- **PDF Report**: Includes structured text with headings and embedded images.

## Example
If the keyword is **"Geo-political Tension"**, the tool will:
- Search relevant content on trusted sites (e.g., Bloomberg, Forbes, etc.).
- Scrape and store related text and images.
- Generate `scraped_data.json` and `content_document.pdf` in the output folder.

## License
This project is open-source. Feel free to modify and enhance it!

## Disclaimer
Use this scraper responsibly. Ensure compliance with website terms and conditions before extracting data.

