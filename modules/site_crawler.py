import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from config import SITE_INDEX_FILE

class SiteCrawler:
    def __init__(self, base_url: str):
        self.base_url = base_url.strip().rstrip('/')
        self.domain = urlparse(self.base_url).netloc
        self.visited_urls = set()
        self.indexed_pages = []

    def crawl(self, max_pages: int = 30):
        if not self.base_url:
            return {"status": "error", "message": "No base URL provided"}

        print(f"Starting crawl for {self.base_url}...")
        urls_to_visit = [self.base_url]
        
        # Try checking sitemap first
        sitemap_url = f"{self.base_url}/sitemap.xml"
        try:
            resp = requests.get(sitemap_url, timeout=5)
            if resp.status_code == 200 and "<loc>" in resp.text:
                soup = BeautifulSoup(resp.text, 'xml')
                locs = [loc.text.strip() for loc in soup.find_all('loc')]
                if locs:
                    urls_to_visit = list(set(urls_to_visit + locs))[:max_pages]
        except Exception as e:
            print(f"Sitemap check skipped: {e}")

        while urls_to_visit and len(self.indexed_pages) < max_pages:
            url = urls_to_visit.pop(0)
            if url in self.visited_urls:
                continue

            self.visited_urls.add(url)
            try:
                res = requests.get(url, timeout=7, headers={"User-Agent": "SEO-Bot-Crawler/1.0"})
                if res.status_code != 200 or "text/html" not in res.headers.get("Content-Type", ""):
                    continue

                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Extract page title and description
                title = soup.title.string.strip() if soup.title and soup.title.string else url
                meta_desc = ""
                meta_tag = soup.find("meta", attrs={"name": "description"})
                if meta_tag and meta_tag.get("content"):
                    meta_desc = meta_tag["content"].strip()
                
                # Extract H1 headings
                h1_tags = [h1.get_text().strip() for h1 in soup.find_all("h1") if h1.get_text().strip()]

                page_info = {
                    "url": url,
                    "title": title,
                    "description": meta_desc,
                    "headings": h1_tags[:3],
                    "path": urlparse(url).path
                }

                self.indexed_pages.append(page_info)
                print(f"Indexed: {title} ({url})")

                # Find internal links
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag['href']
                    full_url = urljoin(self.base_url, href)
                    parsed_full = urlparse(full_url)
                    
                    if parsed_full.netloc == self.domain and full_url not in self.visited_urls:
                        # Filter out static assets
                        if not any(full_url.endswith(ext) for ext in ['.png', '.jpg', '.css', '.js', '.pdf']):
                            urls_to_visit.append(full_url)

            except Exception as e:
                print(f"Error crawling {url}: {e}")

        # Save to JSON index
        self.save_index()
        return {"status": "success", "count": len(self.indexed_pages), "pages": self.indexed_pages}

    def save_index(self):
        with open(SITE_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(self.indexed_pages, f, indent=4, ensure_ascii=False)
        print(f"Saved {len(self.indexed_pages)} indexed pages to {SITE_INDEX_FILE}")

def load_site_index():
    if SITE_INDEX_FILE.exists():
        try:
            with open(SITE_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []
