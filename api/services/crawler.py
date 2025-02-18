import trafilatura
import asyncio
from typing import List, Optional, Dict, Set, Tuple
from ratelimit import limits, sleep_and_retry
from bs4 import BeautifulSoup
import httpx
from .embeddings import generate_embeddings
from .storage import SupabaseClient
import os
import json
from urllib.parse import urljoin, urlparse

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
        return any(pattern in url.lower() for pattern in self.doc_patterns)

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract and normalize links from HTML content"""
        soup = BeautifulSoup(html, 'lxml')
        links = []
        base_domain = urlparse(base_url).netloc
        
        for a in soup.find_all('a', href=True):
            url = urljoin(base_url, a['href'])
            parsed = urlparse(url)
            
            # Remove hash fragment and normalize URL
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"
                
            # Only include links from same domain and matching doc patterns
            # that we haven't seen before (no duplicates from hash fragments)
            if (parsed.netloc == base_domain and 
                self._is_documentation_url(clean_url) and 
                clean_url not in links):
                links.append(clean_url)
        
        print(f"Found {len(links)} unique documentation links on {base_url}")
        return links

    @sleep_and_retry
    @limits(calls=MAX_REQUESTS, period=ONE_MINUTE)
    async def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content with rate limiting"""
        try:
            print(f"Fetching URL: {url}")
            response = await self.http_client.get(url)
            response.raise_for_status()
            print(f"Successfully fetched {url} (Status: {response.status_code})")
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            if isinstance(e, httpx.HTTPError):
                print(f"HTTP Status: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
            return None

    def _extract_content(self, html: str) -> Optional[Dict[str, str]]:
        """Extract main content using Trafilatura with API docs optimization"""
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
                print("Trafilatura extraction failed, trying API docs specific extraction")
                api_content_elements = soup.select(
                    'main, article, .content, .documentation, .api-content, ' +
                    '.endpoint-description, .method-description, .api-docs'
                )
                if api_content_elements:
                    content = ' '.join(elem.get_text(strip=True, separator=' ') 
                                     for elem in api_content_elements)

            if not content:
                print("Content extraction failed")
                return None

            print(f"Successfully extracted content (Length: {len(content)})")
            return {
                "title": title,
                "content": content
            }
        except Exception as e:
            print(f"Error extracting content: {str(e)}")
            return None

    def _chunk_content(self, content: str) -> List[str]:
        """Implement hybrid chunking strategy"""
        print(f"Chunking content of length {len(content)}")
        
        if len(content) < 1000:
            print("Content under 1000 chars, using as single chunk")
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
        
        print(f"Split content into {len(chunks)} chunks")
        return chunks

    async def _process_url(self, url: str, parent_url: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Process a single URL and return success status and found links"""
        try:
            print(f"\nProcessing URL: {url}")
            
            # Fetch content
            html = await self._fetch_url(url)
            if not html:
                print(f"Failed to fetch content from {url}")
                return False, []

            # Extract content
            extracted = self._extract_content(html)
            if not extracted:
                print(f"Failed to extract content from {url}")
                return False, []

            # Extract links for recursive crawling
            links = self._extract_links(html, url)

            # Chunk content
            chunks = self._chunk_content(extracted["content"])
            print(f"Processing {len(chunks)} chunks from {url}")

            # Update total chunks count
            self.chunks_total += len(chunks)
            
            # Generate embeddings and store
            successful_chunks = 0
            for i, chunk in enumerate(chunks, 1):
                print(f"Processing chunk {i}/{len(chunks)} from {url}")
                embedding = await generate_embeddings(chunk)
                if embedding:
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
                    else:
                        print(f"Failed to store chunk {i} from {url}")

            print(f"Successfully processed {successful_chunks}/{len(chunks)} chunks from {url}")
            return successful_chunks > 0, links
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            return False, []

    async def crawl_with_progress(
        self,
        url: str,
        recursive: bool = False,
        max_depth: int = 1
    ):
        """
        Crawl documentation from a URL with progress updates
        """
        print(f"\nStarting crawl of {url} (recursive={recursive}, max_depth={max_depth})")
        processed_urls = set()
        urls_to_process = [(url, 0)]  # (url, depth)
        
        # Reset progress counters
        self.chunks_processed = 0
        self.chunks_total = 0
        
        while urls_to_process:
            # Yield current progress
            yield {
                "status": "processing",
                "urls_processed": len(processed_urls),
                "urls_discovered": len(urls_to_process) + len(processed_urls),
                "chunks_processed": self.chunks_processed,
                "chunks_total": self.chunks_total or 1  # Avoid division by zero
            }
            
            current_url, depth = urls_to_process.pop(0)
            
            if current_url in processed_urls:
                print(f"Skipping already processed URL: {current_url}")
                continue
                
            success, links = await self._process_url(current_url, parent_url=url if depth > 0 else None)
            if success:
                processed_urls.add(current_url)
                print(f"Successfully processed {current_url}")
                
                # Handle recursive crawling
                if recursive and depth < max_depth:
                    new_depth = depth + 1
                    print(f"Adding {len(links)} links at depth {new_depth}")
                    # Add new links to process with incremented depth
                    urls_to_process.extend([(link, new_depth) for link in links])
        
        # Final progress update
        yield {
            "status": "complete",
            "urls_processed": len(processed_urls),
            "urls_discovered": len(processed_urls),
            "chunks_processed": self.chunks_processed,
            "chunks_total": self.chunks_total,
            "urls_list": list(processed_urls)
        }

    async def get_status(self, job_id: str) -> dict:
        """Get status of a crawl job"""
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        return self.active_jobs[job_id]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
