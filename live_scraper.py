"""
High-Performance Live Data Scraper for Mixed Sources
Handles HTML pages, PDFs with parallel processing and smart caching
"""
import asyncio
import aiohttp
import aiofiles
from pathlib import Path
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import hashlib
from concurrent.futures import ThreadPoolExecutor
import pdfplumber
from bs4 import BeautifulSoup
import time

# Configuration
SOURCES_CSV = Path("sources.csv")
DATA_RAW_DIR = Path("data_raw")
DATA_PROCESSED_DIR = Path("data_processed")
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Performance settings (can be overridden via config.yaml)
try:
    from config_loader import get_config
    config = get_config()
    MAX_CONCURRENT_REQUESTS = config.get('scraper.max_concurrent_requests', 10)
    REQUEST_TIMEOUT = config.get('scraper.request_timeout', 15)
    CACHE_TTL_HOURS = config.get('scraper.cache_ttl_hours', 24)
except ImportError:
    # Fallback if config not available
    MAX_CONCURRENT_REQUESTS = 10
    REQUEST_TIMEOUT = 15
    CACHE_TTL_HOURS = 24

RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds

# User agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
]

class LiveScraper:
    def __init__(self):
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=5)  # For PDF processing
        self.cache = {}
        self.load_cache()
    
    def load_cache(self):
        """Load cache metadata"""
        cache_file = CACHE_DIR / "cache_metadata.json"
        if cache_file.exists():
            with open(cache_file, "r") as f:
                self.cache = json.load(f)
    
    def save_cache(self):
        """Save cache metadata"""
        cache_file = CACHE_DIR / "cache_metadata.json"
        with open(cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)
    
    def get_cache_key(self, url: str) -> str:
        """Generate cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = datetime.fromisoformat(self.cache[cache_key]["timestamp"])
        age = datetime.now() - cached_time
        return age < timedelta(hours=CACHE_TTL_HOURS)
    
    async def fetch_url(self, url: str, source_id: str, retry_count: int = 0) -> Optional[bytes]:
        """Fetch URL with retry logic"""
        cache_key = self.get_cache_key(url)
        
        # Check cache first
        if self.is_cache_valid(cache_key):
            cache_file = CACHE_DIR / f"{cache_key}.cache"
            if cache_file.exists():
                print(f"  ✓ Using cache for {source_id}")
                async with aiofiles.open(cache_file, "rb") as f:
                    return await f.read()
        
        try:
            headers = {
                "User-Agent": USER_AGENTS[hash(url) % len(USER_AGENTS)],
                "Accept": "text/html,application/pdf,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            async with self.session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Save to cache
                    cache_file = CACHE_DIR / f"{cache_key}.cache"
                    async with aiofiles.open(cache_file, "wb") as f:
                        await f.write(content)
                    
                    self.cache[cache_key] = {
                        "url": url,
                        "timestamp": datetime.now().isoformat(),
                        "size": len(content),
                    }
                    
                    return content
                elif response.status == 403:
                    print(f"  ⚠️  {source_id}: Access forbidden (403) - may need authentication")
                    return None
                elif response.status == 404:
                    print(f"  ⚠️  {source_id}: Not found (404)")
                    return None
                else:
                    print(f"  ⚠️  {source_id}: HTTP {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            if retry_count < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self.fetch_url(url, source_id, retry_count + 1)
            print(f"  ❌ {source_id}: Timeout after {RETRY_ATTEMPTS} retries")
            return None
        except Exception as e:
            if retry_count < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self.fetch_url(url, source_id, retry_count + 1)
            print(f"  ❌ {source_id}: Error - {e}")
            return None
    
    def extract_text_from_pdf(self, content: bytes, source_id: str) -> str:
        """Extract text from PDF using pdfplumber (fast)"""
        try:
            import io
            pdf_file = io.BytesIO(content)
            
            text_parts = []
            with pdfplumber.open(pdf_file) as pdf:
                # Process first 50 pages for speed (most facts are in first pages)
                max_pages = min(50, len(pdf.pages))
                for page in pdf.pages[:max_pages]:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            
            return "\n".join(text_parts)
        except Exception as e:
            print(f"  ⚠️  {source_id}: PDF extraction error - {e}")
            return ""
    
    def extract_text_from_html(self, content: bytes, source_id: str) -> str:
        """Extract text from HTML using BeautifulSoup"""
        try:
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator="\n")
            
            # Clean up
            lines = [line.strip() for line in text.split("\n")]
            lines = [line for line in lines if line]
            
            return "\n".join(lines)
        except Exception as e:
            print(f"  ⚠️  {source_id}: HTML extraction error - {e}")
            return ""
    
    async def process_source(self, source_id: str, source_url: str, source_type: str) -> Tuple[bool, str]:
        """Process a single source"""
        print(f"Processing {source_id} ({source_type})...")
        
        # Fetch content
        content = await self.fetch_url(source_url, source_id)
        if not content:
            return False, ""
        
        # Extract text based on source type
        if source_type in ["sid_pdf", "kim_pdf", "factsheet_consolidated"] or source_url.endswith(".pdf"):
            # PDF - run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                self.executor,
                self.extract_text_from_pdf,
                content,
                source_id
            )
        else:
            # HTML
            text = self.extract_text_from_html(content, source_id)
        
        if not text or len(text.strip()) < 100:
            print(f"  ⚠️  {source_id}: Extracted text too short or empty")
            return False, text
        
        # Save raw content
        DATA_RAW_DIR.mkdir(exist_ok=True)
        if source_url.endswith(".pdf"):
            raw_file = DATA_RAW_DIR / f"{source_id}.pdf"
            async with aiofiles.open(raw_file, "wb") as f:
                await f.write(content)
        else:
            raw_file = DATA_RAW_DIR / f"{source_id}.html"
            async with aiofiles.open(raw_file, "wb") as f:
                await f.write(content)
        
        # Save processed text
        DATA_PROCESSED_DIR.mkdir(exist_ok=True)
        processed_file = DATA_PROCESSED_DIR / f"{source_id}.txt"
        async with aiofiles.open(processed_file, "w", encoding="utf-8") as f:
            await f.write(text)
        
        # Save metadata
        meta = {
            "source_id": source_id,
            "source_url": source_url,
            "source_type": source_type,
            "http_status": 200,
            "content_length_bytes": len(content),
            "text_length_chars": len(text),
            "fetched_at": datetime.now().isoformat(),
        }
        meta_file = DATA_PROCESSED_DIR / f"{source_id}_meta.json"
        async with aiofiles.open(meta_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(meta, indent=2))
        
        print(f"  ✓ {source_id}: {len(text)} chars extracted")
        return True, text
    
    async def scrape_all(self, force_refresh: bool = False):
        """Scrape all sources in parallel"""
        # Load sources
        sources = []
        with open(SOURCES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sources.append({
                    "source_id": row["source_id"],
                    "source_url": row["source_url"],
                    "source_type": row["source_type"],
                })
        
        print(f"Scraping {len(sources)} sources (parallel, max {MAX_CONCURRENT_REQUESTS} concurrent)...")
        print("=" * 70)
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        
        async def process_with_semaphore(source):
            async with semaphore:
                return await self.process_source(
                    source["source_id"],
                    source["source_url"],
                    source["source_type"]
                )
        
        # Process all sources in parallel
        start_time = time.time()
        tasks = [process_with_semaphore(source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        # Summary
        successful = sum(1 for r in results if isinstance(r, tuple) and r[0])
        failed = len(results) - successful
        
        print("=" * 70)
        print(f"✓ Scraping complete: {successful} successful, {failed} failed")
        print(f"⏱️  Time taken: {elapsed:.2f} seconds ({elapsed/len(sources):.2f}s per source)")
        
        # Save cache
        self.save_cache()
        
        # Auto-rebuild index if scraping was successful (from config)
        auto_rebuild = True
        try:
            from config_loader import get_config
            config = get_config()
            auto_rebuild = config.get('scraper.auto_rebuild_index', True)
        except ImportError:
            pass
        
        if auto_rebuild and successful and len(successful) > 0:
            try:
                print("\n🔄 Auto-rebuilding FAISS index after scraper update...")
                import subprocess
                result = subprocess.run(
                    ["python", "rebuild_index.py"],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                if result.returncode == 0:
                    print("✓ Index rebuilt successfully")
                else:
                    print(f"⚠️  Index rebuild failed: {result.stderr[:200]}")
            except Exception as e:
                print(f"⚠️  Could not auto-rebuild index: {e}")
                print("   Please run 'python rebuild_index.py' manually")
        
        return successful, failed
    
    async def refresh_stale_sources(self):
        """Refresh only sources that are stale (older than cache TTL)"""
        sources = []
        with open(SOURCES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache_key = self.get_cache_key(row["source_url"])
                if not self.is_cache_valid(cache_key):
                    sources.append({
                        "source_id": row["source_id"],
                        "source_url": row["source_url"],
                        "source_type": row["source_type"],
                    })
        
        if not sources:
            print("All sources are up-to-date (within cache TTL)")
            return
        
        print(f"Refreshing {len(sources)} stale sources...")
        await self.scrape_all(force_refresh=True)
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        self.executor.shutdown(wait=True)

async def main():
    """Main function"""
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    async with LiveScraper() as scraper:
        if mode == "all":
            await scraper.scrape_all()
        elif mode == "refresh":
            await scraper.refresh_stale_sources()
        else:
            print("Usage: python live_scraper.py [all|refresh]")
            print("  all: Scrape all sources")
            print("  refresh: Only refresh stale sources (faster)")

if __name__ == "__main__":
    asyncio.run(main())

