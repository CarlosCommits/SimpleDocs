import trafilatura
import asyncio
import traceback
from typing import List, Optional, Dict, Set, Tuple, Any
from ratelimit import limits, sleep_and_retry
from bs4 import BeautifulSoup
import httpx
from .embeddings import generate_embeddings
from .storage import SupabaseClient
import os
import json
import logging
import datetime
from urllib.parse import urljoin, urlparse
from . import websocket_server

# Set up file-based logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"crawler_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("crawler")
logger.info(f"Crawler logging initialized. Log file: {log_file}")

ONE_MINUTE = 60
MAX_REQUESTS = int(os.getenv("CRAWLER_RATE_LIMIT", "100"))

class DocumentCrawler:
    def __init__(self, doc_patterns: List[str] = None):
        self.doc_patterns = doc_patterns or [
            '/reference/',
            '/docs/',
            '/api/',
            '/guide/',
            '/documentation/',
            '/tutorial/'
        ]
        self.supabase = SupabaseClient()
        self.active_jobs = {}
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Documentation Crawler; +http://localhost)"
            }
        )
        
        # Progress tracking
        self.chunks_processed = 0
        self.chunks_total = 0

    def _is_documentation_url(self, url: str) -> bool:
        """Check if URL matches documentation patterns"""
        for pattern in self.doc_patterns:
            if pattern in url.lower():
                logger.info(f"URL matched pattern '{pattern}': {url}")
                return True
        logger.info(f"URL did not match any patterns: {url}")
        return False

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and normalize links from HTML content"""
        logger.info(f"\n--- DETAILED LINK EXTRACTION for {base_url} ---")
        soup = BeautifulSoup(html, 'lxml')
        all_links = soup.find_all('a', href=True)
        logger.info(f"Total <a> tags found in HTML: {len(all_links)}")
        
        links = []
        base_domain = urlparse(base_url).netloc
        logger.info(f"Base domain: {base_domain}")
        
        # Log the first 10 links for debugging
        logger.info("First 10 <a> tags:")
        for i, a in enumerate(all_links[:10]):
            logger.info(f"  {i+1}. href='{a['href']}'")
        
        for a in all_links:
            href = a['href']
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            
            # Remove hash fragment and normalize URL
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"
            
            # Debug info about the link
            same_domain = parsed.netloc == base_domain
            is_doc_url = self._is_documentation_url(clean_url)
            is_duplicate = clean_url in links
            
            logger.info(f"Processing link: {clean_url}")
            logger.info(f"  Original href: {href}")
            logger.info(f"  Same domain: {same_domain} (netloc: {parsed.netloc})")
            logger.info(f"  Is doc URL: {is_doc_url}")
            logger.info(f"  Is duplicate: {is_duplicate}")
            
            if (same_domain and is_doc_url and not is_duplicate):
                links.append(clean_url)
                logger.info(f"  ADDED: {clean_url}")
            else:
                logger.info(f"  SKIPPED: {clean_url}")
        
        logger.info(f"Found {len(links)} unique documentation links on {base_url}")
        if links:
            logger.info("Links found:")
            for link in links:
                logger.info(f"  - {link}")
        else:
            logger.info("No documentation links found!")
        
        return links

    @sleep_and_retry
    @limits(calls=MAX_REQUESTS, period=ONE_MINUTE)
    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with rate limiting"""
        try:
            logger.info(f"Fetching URL: {url}")
            response = await self.http_client.get(url)
            response.raise_for_status()
            logger.info(f"Successfully fetched {url} (Status: {response.status_code})")
            content_length = len(response.text)
            logger.info(f"Content length: {content_length} characters")
            
            # Save a sample of the HTML content for debugging
            html_sample = response.text[:1000] + "..." if len(response.text) > 1000 else response.text
            logger.debug(f"HTML sample: {html_sample}")
            
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            if isinstance(e, httpx.HTTPError):
                logger.error(f"HTTP Status: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
            return None

    def _extract_content(self, html: str) -> Optional[Dict[str, str]]:
        """Extract main content using Trafilatura with API docs optimization"""
        try:
            logger.info("Extracting content from HTML")
            
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
            logger.info(f"Page title: {title}")

            # If Trafilatura fails, try extracting from common API doc elements
            if not content:
                logger.info("Trafilatura extraction failed, trying API docs specific extraction")
                api_content_elements = soup.select(
                    'main, article, .content, .documentation, .api-content, ' +
                    '.endpoint-description, .method-description, .api-docs'
                )
                if api_content_elements:
                    logger.info(f"Found {len(api_content_elements)} API content elements")
                    content = ' '.join(elem.get_text(strip=True, separator=' ') 
                                     for elem in api_content_elements)

            if not content:
                logger.error("Content extraction failed")
                return None

            logger.info(f"Successfully extracted content (Length: {len(content)})")
            # Log a sample of the extracted content
            content_sample = content[:500] + "..." if len(content) > 500 else content
            logger.debug(f"Content sample: {content_sample}")
            
            return {
                "title": title,
                "content": content
            }
        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            return None

    def _chunk_content(self, content: str) -> List[str]:
        """Implement hybrid chunking strategy"""
        logger.info(f"Chunking content of length {len(content)}")
        
        if len(content) < 1000:
            logger.info("Content under 1000 chars, using as single chunk")
            return [content]
        
        # Split by common API documentation section markers
        section_markers = [
            "## ", "### ", "#### ",  # Markdown headers
            "Parameters", "Request", "Response",  # Common API doc sections
            "Example", "Returns", "Arguments"
        ]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        # Split into lines and process
        lines = content.split('\n')
        for line in lines:
            # Check if line starts a new section
            is_section_start = any(line.strip().startswith(marker) for marker in section_markers)
            
            if is_section_start and current_chunk:
                # Store current chunk if we hit a new section
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += len(line)
            
            # If chunk gets too large, store it
            if current_length >= 1000:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
        
        # Add any remaining content
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        logger.info(f"Split content into {len(chunks)} chunks")
        return chunks

    async def _process_url(self, url: str, parent_url: Optional[str] = None, ctx = None) -> Tuple[bool, List[str]]:
        """Process a single URL and return success status and found links"""
        try:
            logger.info(f"\n=== Processing URL: {url} ===")
            logger.info(f"Parent URL: {parent_url if parent_url else 'None (root URL)'}")
            
            # Fetch content
            html = await self._fetch_url(url)
            if not html:
                logger.error(f"Failed to fetch content from {url}")
                return False, []

            # Extract content
            extracted = self._extract_content(html)
            if not extracted:
                logger.error(f"Failed to extract content from {url}")
                return False, []

            # Extract links for recursive crawling
            links = self._extract_links(html, url)

            # Chunk content
            chunks = self._chunk_content(extracted["content"])
            logger.info(f"Processing {len(chunks)} chunks from {url}")

            # Update total chunks count
            self.chunks_total += len(chunks)
            logger.info(f"Updated total chunks count: {self.chunks_total}")
            
            # Generate embeddings and store
            successful_chunks = 0
            for i, chunk in enumerate(chunks, 1):
                logger.info(f"Processing chunk {i}/{len(chunks)} from {url}")
                embedding = await generate_embeddings(chunk)
                if embedding:
                    logger.info(f"Generated embedding for chunk {i}, dimension: {len(embedding)}")
                    success = await self.supabase.store_document({
                        "url": url,
                        "title": extracted["title"],
                        "content": chunk,
                        "embedding": embedding,
                        "parent_url": parent_url
                    })
                    if success:
                        successful_chunks += 1
                        self.chunks_processed += 1
                        logger.info(f"Successfully stored chunk {i}")
                        
                        # Report progress if context is provided
                        if ctx:
                            # Simplified progress reporting without named parameters
                            progress = self.chunks_processed / max(self.chunks_total, 1)
                            await ctx.report_progress(
                                progress,
                                f"Processing {url} ({i}/{len(chunks)})"
                            )
                    else:
                        logger.error(f"Failed to store chunk {i} from {url}")
                else:
                    logger.error(f"Failed to generate embedding for chunk {i}")

            logger.info(f"Successfully processed {successful_chunks}/{len(chunks)} chunks from {url}")
            return successful_chunks > 0, links
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False, []

    async def crawl_with_progress(
        self,
        url: str,
        recursive: bool = False,
        max_depth: int = 1,
        ctx = None
    ):
        """
        Crawl documentation from a URL with progress updates
        """
        logger.info(f"\n=== Starting crawl of {url} ===")
        logger.info(f"Settings: recursive={recursive}, max_depth={max_depth}")
        
        # Initialize with empty processed_urls set
        processed_urls = set()
        urls_to_process = [(url, 0)]  # (url, depth)
        
        # Reset progress counters
        self.chunks_processed = 0
        self.chunks_total = 0
        logger.info(f"Reset progress counters: processed={self.chunks_processed}, total={self.chunks_total}")
        
        # Track all discovered URLs for reporting
        all_discovered_urls = set([url])
        
        # Start WebSocket server if not already running
        try:
            # Create task to start WebSocket server (non-blocking)
            ws_server_task = asyncio.create_task(
                websocket_server.start_server()
            )
            logger.info("WebSocket server task created")
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {str(e)}")
        
        while urls_to_process:
            current_url, depth = urls_to_process.pop(0)
            logger.info(f"Processing URL at depth {depth}: {current_url}")
            
            # Prepare progress update
            progress_update = {
                "status": "processing",
                "urls_processed": len(processed_urls),
                "urls_discovered": len(all_discovered_urls),
                "chunks_processed": self.chunks_processed,
                "chunks_total": self.chunks_total or 1,  # Avoid division by zero
                "current_url": current_url
            }
            
            # Send progress update to WebSocket clients
            try:
                await websocket_server.update_progress(progress_update)
            except Exception as e:
                logger.error(f"Error updating WebSocket progress: {str(e)}")
            
            # Yield progress for MCP
            logger.info(f"Progress update: {json.dumps(progress_update)}")
            yield progress_update
            
            if current_url in processed_urls:
                logger.info(f"Skipping already processed URL: {current_url}")
                continue
                
            success, links = await self._process_url(current_url, parent_url=url if depth > 0 else None, ctx=ctx)
            if success:
                # Only add to processed_urls after successful processing
                processed_urls.add(current_url)
                logger.info(f"Successfully processed {current_url}")
                logger.info(f"Total processed URLs: {len(processed_urls)}")
                
                # Update progress with the newly processed URL
                progress_update["urls_processed"] = len(processed_urls)
                progress_update["urls_list"] = list(processed_urls)
                try:
                    await websocket_server.update_progress(progress_update)
                except Exception as e:
                    logger.error(f"Error updating WebSocket progress: {str(e)}")
                
                # Handle recursive crawling
                if recursive and depth < max_depth:
                    new_depth = depth + 1
                    logger.info(f"Adding {len(links)} links at depth {new_depth}")
                    
                    # Add new links to process with incremented depth
                    for link in links:
                        if link not in processed_urls and link not in [u for u, _ in urls_to_process]:
                            urls_to_process.append((link, new_depth))
                            all_discovered_urls.add(link)
                            logger.info(f"Added to processing queue: {link}")
                        else:
                            logger.info(f"Skipping already queued/processed link: {link}")
                else:
                    if not recursive:
                        logger.info("Recursive crawling disabled, not adding links")
                    elif depth >= max_depth:
                        logger.info(f"Reached max depth ({max_depth}), not adding more links")
            else:
                logger.error(f"Failed to process {current_url}")
        
        # Final progress update
        final_update = {
            "status": "complete",
            "urls_processed": len(processed_urls),
            "urls_discovered": len(all_discovered_urls),
            "chunks_processed": self.chunks_processed,
            "chunks_total": self.chunks_total,
            "urls_list": list(processed_urls),
            "current_url": ""
        }
        
        # Send final update to WebSocket clients
        try:
            await websocket_server.update_progress(final_update)
        except Exception as e:
            logger.error(f"Error updating WebSocket progress: {str(e)}")
            
        logger.info(f"Final progress update: {json.dumps(final_update)}")
        yield final_update

    async def crawl(
        self,
        url: str,
        recursive: bool = False,
        max_depth: int = 1,
        ctx = None
    ):
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
