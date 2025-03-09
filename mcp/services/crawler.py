import trafilatura
import asyncio
import traceback
from typing import List, Optional, Dict, Set, Tuple, Any
from ratelimit import limits, sleep_and_retry
from bs4 import BeautifulSoup
import httpx
from .embeddings import generate_embeddings, generate_embeddings_batch
from .storage import SupabaseClient
import os
import json
import logging
import datetime
from urllib.parse import urljoin, urlparse
from . import websocket_server

# Set up file-based logging with robust error handling
try:
    # Use absolute path with WORKING_DIR environment variable if available
    working_dir = os.getenv("WORKING_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(working_dir, "mcp", "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"crawler_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Create a file handler and set its level and formatter
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Get the logger and add the handler
    logger = logging.getLogger("crawler")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    # Add a console handler to see logs in terminal too
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Crawler logging initialized. Log file: {log_file}")
    print(f"Crawler log file: {log_file}")  # Print to console for visibility
except Exception as e:
    print(f"Error setting up logging: {str(e)}")
    # Set up a basic console logger as fallback
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("crawler")
    logger.warning(f"Failed to set up file logging. Using console logging only. Error: {str(e)}")

ONE_MINUTE = 60
MAX_REQUESTS = int(os.getenv("CRAWLER_RATE_LIMIT", "300"))

class DocumentCrawler:
    def __init__(self, doc_patterns: List[str] = None, max_concurrent_scrapes: int = 30):
        self.doc_patterns = doc_patterns or [
            '/reference/', '/docs/', '/api/', '/guide/', '/documentation/', '/tutorial/'
        ]
        self.supabase = SupabaseClient()
        self.active_jobs = {}
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Documentation Crawler; +http://localhost)"}
        )
        self.chunks_processed = 0
        self.chunks_total = 0
        self.html_cache = {}  # Cache HTML to avoid refetching
        self.max_concurrent_scrapes = max_concurrent_scrapes  # Limit concurrent scraping tasks

    def _is_documentation_url(self, url: str) -> bool:
        """Check if URL matches documentation patterns - optimized for speed"""
        url_lower = url.lower()
        for pattern in self.doc_patterns:
            if pattern in url_lower:
                return True
        return False
        
    def _get_parent_url(self, url: str) -> Optional[str]:
        """
        Determine parent URL based on documentation patterns
        For example, if URL is https://example.com/docs/topic, 
        parent URL would be https://example.com/docs/
        """
        url_lower = url.lower()
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        for pattern in self.doc_patterns:
            if pattern in url_lower:
                # Find the position of the pattern in the path
                path = parsed.path
                pattern_pos = path.lower().find(pattern)
                if pattern_pos >= 0:
                    # Extract the path up to and including the pattern
                    parent_path = path[:pattern_pos + len(pattern)]
                    return f"{base_url}{parent_path}"
        
        # If no pattern matches, return None
        return None

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and normalize links from HTML content - optimized for speed"""
        soup = BeautifulSoup(html, 'lxml')
        all_links = soup.find_all('a', href=True)
        logger.debug(f"Found {len(all_links)} links in {base_url}")
        
        links = []
        base_domain = urlparse(base_url).netloc
        
        # Process links in a more efficient way with less logging
        for a in all_links:
            href = a['href']
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            
            # Remove hash fragment and normalize URL
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"
            
            # Check if this is a valid documentation URL
            same_domain = parsed.netloc == base_domain
            is_doc_url = self._is_documentation_url(clean_url)
            is_duplicate = clean_url in links
            
            if (same_domain and is_doc_url and not is_duplicate):
                links.append(clean_url)
        
        logger.info(f"Found {len(links)} unique documentation links on {base_url}")
        return links

    @sleep_and_retry
    @limits(calls=MAX_REQUESTS, period=ONE_MINUTE)
    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with rate limiting - optimized for speed"""
        try:
            # Minimal logging to improve performance
            logger.debug(f"Fetching URL: {url}")
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            # Only log success at debug level
            logger.debug(f"Successfully fetched {url} (Status: {response.status_code}, Length: {len(response.text)})")
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            if isinstance(e, httpx.HTTPError):
                logger.error(f"HTTP Status: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
            return None

    def _extract_content(self, html: str) -> Optional[Dict[str, str]]:
        """Extract main content using Trafilatura with API docs optimization - optimized for speed"""
        try:
            # First try Trafilatura for content extraction
            content = trafilatura.extract(
                html,
                include_tables=True,
                include_links=True,
                include_images=False,
                no_fallback=False
            )
            
            # Parse HTML for metadata and backup content extraction
            soup = BeautifulSoup(html, 'lxml')
            title = soup.title.string if soup.title else None

            # If Trafilatura fails, try extracting from common API doc elements
            if not content:
                logger.debug("Trafilatura extraction failed, trying API docs specific extraction")
                api_content_elements = soup.select(
                    'main, article, .content, .documentation, .api-content, ' +
                    '.endpoint-description, .method-description, .api-docs'
                )
                if api_content_elements:
                    content = ' '.join(elem.get_text(strip=True, separator=' ') 
                                     for elem in api_content_elements)

            if not content:
                logger.error("Content extraction failed")
                return None

            logger.debug(f"Extracted content (Length: {len(content)})")
            
            return {
                "title": title,
                "content": content
            }
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            return None

    def _prepare_content(self, title: Optional[str], content: str) -> str:
        """
        Prepare content for embedding by combining title and content
        This improves search quality by including title keywords in the embedding
        """
        if title:
            # Combine title and content for better search results
            return f"Title: {title}\n\nContent: {content}"
        return content

    async def _process_url(self, url: str, parent_url: Optional[str] = None, ctx=None) -> Tuple[bool, Dict]:
        """Process a single URL and return success status and document data"""
        try:
            logger.debug(f"Processing URL: {url}")
            
            # Use cached HTML or fetch if not cached
            html = self.html_cache.get(url)
            if not html:
                html = await self._fetch_url(url)
                if not html:
                    logger.error(f"Failed to fetch content from {url}")
                    return False, {}
                self.html_cache[url] = html

            # Extract content
            extracted = self._extract_content(html)
            if not extracted:
                logger.error(f"Failed to extract content from {url}")
                return False, {}

            # Prepare content by combining title and content for better search results
            prepared_content = self._prepare_content(extracted["title"], extracted["content"])
            
            # Return the document data for batch processing
            return True, {
                "url": url,
                "title": extracted["title"],
                "content": extracted["content"],
                "prepared_content": prepared_content,
                "parent_url": parent_url
            }
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False, []

    async def crawl_with_progress(self, url: str, recursive: bool = False, max_depth: int = 1, ctx=None):
        """
        Crawl documentation from a URL with progress updates, then scrape all URLs simultaneously
        """
        logger.info(f"\n=== Starting crawl of {url} ===")
        logger.info(f"Settings: recursive={recursive}, max_depth={max_depth}")

        # Reset progress.json at the start of a new crawl
        try:
            initial_progress = {
                "status": "crawling",
                "urls_crawled": 0,
                "urls_fully_processed": 0,
                "urls_discovered": 0,  # Start with 0, will be updated after first URL is processed
                "chunks_processed": 0,
                "chunks_total": 0,
                "current_url": url,
                "urls_list": [],
                "last_updated": datetime.datetime.now().isoformat()
            }
            await websocket_server.update_progress(initial_progress)
            
            # Add the initial URL to the discovered count in a separate update
            # This ensures our reset logic in websocket_server.py works correctly
            await asyncio.sleep(0.1)  # Small delay to ensure reset happens first
            await websocket_server.update_progress({
                "urls_discovered": 1  # Now add the initial URL
            })
        except Exception as e:
            logger.error(f"Error resetting progress: {str(e)}")

        # Phase 1: Crawling - Collect all URLs in parallel
        logger.info("Starting crawling phase")
        crawled_urls = set()  # URLs that have been crawled for links
        fully_processed_urls = set()  # URLs that have been fully processed (embedded)
        urls_to_process = [(url, 0)]  # (url, depth)
        all_urls_to_scrape = set([url])
        
        # Track parent-child relationships for URLs
        url_parents = {}  # Maps URL to its parent URL
        
        # Semaphore to limit concurrent crawling
        crawl_semaphore = asyncio.Semaphore(self.max_concurrent_scrapes)
        
        async def process_url_for_links(url: str, depth: int):
            """Process a single URL to extract links"""
            async with crawl_semaphore:
                if url in crawled_urls:
                    logger.info(f"Skipping already crawled URL: {url}")
                    return []
                
                # Fetch HTML and cache it
                html = await self._fetch_url(url)
                if not html:
                    logger.error(f"Failed to fetch content from {url}")
                    return []
                self.html_cache[url] = html
                
                # Extract links for recursive crawling
                links = self._extract_links(html, url)
                crawled_urls.add(url)
                
                # Update progress
                progress_update = {
                    "status": "crawling",
                    "urls_crawled": len(crawled_urls),
                    "urls_fully_processed": len(fully_processed_urls),
                    "urls_discovered": len(all_urls_to_scrape),
                    "current_url": url
                }
                try:
                    await websocket_server.update_progress(progress_update)
                except Exception as e:
                    logger.error(f"Error updating WebSocket progress: {str(e)}")
                
                return links
        
        # Process URLs in waves based on depth
        current_depth = 0
        while urls_to_process and current_depth <= max_depth:
            # Filter URLs at the current depth
            current_wave = [(u, d) for u, d in urls_to_process if d == current_depth]
            urls_to_process = [(u, d) for u, d in urls_to_process if d != current_depth]
            
            if not current_wave:
                current_depth += 1
                continue
                
            logger.info(f"Processing {len(current_wave)} URLs at depth {current_depth}")
            
            # Process all URLs at this depth in parallel
            tasks = [process_url_for_links(url, depth) for url, depth in current_wave]
            results = await asyncio.gather(*tasks)
            
            # Process results and add new URLs to queue
            if recursive and current_depth < max_depth:
                new_depth = current_depth + 1
                for url_depth, links in zip(current_wave, results):
                    source_url = url_depth[0]
                    logger.info(f"Found {len(links)} links from {source_url}")
                    for link in links:
                        if link not in crawled_urls and link not in [u for u, _ in urls_to_process]:
                            urls_to_process.append((link, new_depth))
                            all_urls_to_scrape.add(link)
                            # Track parent-child relationship
                            url_parents[link] = source_url
                            logger.debug(f"Set parent for {link} to {source_url}")
                        else:
                            logger.debug(f"Skipping already queued/crawled link: {link}")
            
            # Update progress after processing this wave
            progress_update = {
                "status": "crawling",
                "urls_crawled": len(crawled_urls),
                "urls_fully_processed": len(fully_processed_urls),
                "urls_discovered": len(all_urls_to_scrape),
                "current_url": "Processing multiple URLs"
            }
            try:
                await websocket_server.update_progress(progress_update)
            except Exception as e:
                logger.error(f"Error updating WebSocket progress: {str(e)}")
            
            yield progress_update
            current_depth += 1

        # Phase 2: Scraping - Process all URLs in parallel
        logger.info("Starting scraping phase")
        self.chunks_processed = 0
        self.chunks_total = 0

        # Semaphore to limit concurrent scrapes
        semaphore = asyncio.Semaphore(self.max_concurrent_scrapes)

        async def bounded_process_url(url: str, parent_url: Optional[str] = None):
            async with semaphore:
                try:
                    logger.info(f"Starting to process URL: {url}")
                    success, doc_data = await self._process_url(url, parent_url, ctx)
                    
                    if success:
                        logger.info(f"Successfully processed URL: {url}")
                        return True, doc_data
                    else:
                        logger.error(f"Failed to process URL: {url} - Content extraction failed")
                        # Log detailed information about the failed URL
                        html = self.html_cache.get(url)
                        if html:
                            logger.debug(f"HTML content length for failed URL {url}: {len(html)}")
                            # Check if there's a title
                            try:
                                soup = BeautifulSoup(html, 'lxml')
                                title = soup.title.string if soup.title else "No title found"
                                logger.debug(f"Title of failed URL {url}: {title}")
                            except Exception as e:
                                logger.error(f"Error parsing HTML for failed URL {url}: {str(e)}")
                        else:
                            logger.error(f"No HTML content cached for failed URL {url}")
                        return False, None
                except Exception as e:
                    logger.error(f"Unexpected error processing URL {url}: {str(e)}")
                    logger.error(f"Stack trace for {url}: {traceback.format_exc()}")
                    return False, None

        # Create tasks for all URLs with pattern-based parent URLs
        tasks = []
        for url in all_urls_to_scrape:
            # Determine parent URL based on URL pattern
            parent_url = self._get_parent_url(url)
            logger.debug(f"Determined parent URL for {url}: {parent_url}")
            tasks.append(bounded_process_url(url, parent_url))
            
        # Process URLs and collect document data
        logger.info(f"Processing {len(tasks)} URLs for content extraction")
        document_batch = []
        batch_size = 20  # Process 20 documents at a time
        
        # Process all URLs and collect their document data
        results = await asyncio.gather(*tasks)
        for success, doc_data in results:
            if success and doc_data:
                document_batch.append(doc_data)
                
        # Process document batches
        if document_batch:
            logger.info(f"Processing {len(document_batch)} documents in batches of {batch_size}")
            self.chunks_total = len(document_batch)
            
            # Process in batches
            for i in range(0, len(document_batch), batch_size):
                batch = document_batch[i:i+batch_size]
                
                # Extract prepared content for embedding
                prepared_contents = [doc["prepared_content"] for doc in batch]
                
                # Generate embeddings in a single batch call
                logger.info(f"Generating embeddings for batch of {len(batch)} documents")
                embeddings = await generate_embeddings_batch(prepared_contents)
                
                # Store documents with embeddings
                successful_docs = 0
                for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                    if embedding:
                        # Store document with embedding
                        success = await self.supabase.store_document({
                            "url": doc["url"],
                            "title": doc["title"],
                            "content": doc["content"],
                            "embedding": embedding,
                            "parent_url": doc["parent_url"]
                        })
                        
                        if success:
                            successful_docs += 1
                            self.chunks_processed += 1
                            fully_processed_urls.add(doc["url"])
                        else:
                            logger.error(f"Failed to store document for URL: {doc['url']}")
                    else:
                        logger.error(f"Failed to generate embedding for URL: {doc['url']}")
                
                # Update progress after each batch
                progress_update = {
                    "status": "scraping",
                    "urls_crawled": len(crawled_urls),
                    "urls_fully_processed": len(fully_processed_urls),
                    "urls_discovered": len(all_urls_to_scrape),
                    "chunks_processed": self.chunks_processed,
                    "chunks_total": self.chunks_total,
                    "current_url": f"Processed batch {i//batch_size + 1}/{(len(document_batch) + batch_size - 1)//batch_size}"
                }
                
                try:
                    await websocket_server.update_progress(progress_update)
                except Exception as e:
                    logger.error(f"Error updating WebSocket progress: {str(e)}")
                
                logger.info(f"Processed batch {i//batch_size + 1}: {successful_docs}/{len(batch)} documents successful")
                yield progress_update

        # Final progress update
        final_update = {
            "status": "complete",
            "urls_crawled": len(crawled_urls),
            "urls_fully_processed": len(fully_processed_urls),
            "urls_discovered": len(all_urls_to_scrape),
            "chunks_processed": self.chunks_processed,
            "chunks_total": self.chunks_total,
            "urls_list": list(fully_processed_urls),
            "current_url": ""
        }
        try:
            await websocket_server.update_progress(final_update)
        except Exception as e:
            logger.error(f"Error updating WebSocket progress: {str(e)}")
        logger.info(f"Final progress update: {json.dumps(final_update)}")
        yield final_update

    async def crawl(self, url: str, recursive: bool = False, max_depth: int = 1, ctx=None):
        """
        Crawl documentation from a URL and return final results
        
        Parameters:
        - url: URL to crawl
        - recursive: Whether to crawl linked pages
        - max_depth: Maximum depth for recursive crawling
        - ctx: MCP context for progress reporting
        """
        last_result = None
        async for result in self.crawl_with_progress(
            url=url,
            recursive=recursive,
            max_depth=max_depth,
            ctx=ctx
        ):
            last_result = result
            if result["status"] == "complete":
                return result
        return last_result

    async def get_status(self, job_id: str) -> dict:
        """Get status of a crawl job"""
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        return self.active_jobs[job_id]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

if __name__ == "__main__":
    async def test_crawl():
        async with DocumentCrawler() as crawler:
            async for result in crawler.crawl_with_progress("https://example.com/docs", recursive=True, max_depth=2):
                print(result)

    asyncio.run(test_crawl())
