#!/usr/bin/env python3
"""
Standalone script to test the DocumentCrawler outside of the MCP framework.
This helps isolate issues with the crawler vs. issues with the MCP integration.
"""

import asyncio
import os
import sys
import json
import traceback
import httpx
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin, urlparse
import logging

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_crawler")

# Copy of the DocumentCrawler class to avoid circular imports
class SimpleCrawler:
    def __init__(self):
        self.doc_patterns = [
            '/reference/',
            '/docs/',
            '/api/',
            '/guide/',
            '/documentation/',
            '/tutorial/'
        ]
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
        self.processed_urls = set()
        
    def _is_documentation_url(self, url: str) -> bool:
        """Check if URL matches documentation patterns"""
        for pattern in self.doc_patterns:
            if pattern in url.lower():
                logger.info(f"URL matched pattern '{pattern}': {url}")
                return True
        logger.info(f"URL did not match any patterns: {url}")
        return False

    def _extract_links(self, html: str, base_url: str) -> list:
        """Extract and normalize links from HTML content"""
        logger.info(f"Extracting links from {base_url}")
        soup = BeautifulSoup(html, 'html.parser')
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

    async def fetch_url(self, url: str) -> str:
        """Fetch URL content"""
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
            return ""

    async def crawl(self, url: str, recursive: bool = False, max_depth: int = 1):
        """Crawl documentation from a URL"""
        logger.info(f"Starting crawl of {url} (recursive={recursive}, max_depth={max_depth})")
        
        # Reset state
        self.processed_urls = set()
        urls_to_process = [(url, 0)]  # (url, depth)
        
        while urls_to_process:
            current_url, depth = urls_to_process.pop(0)
            
            if current_url in self.processed_urls:
                logger.info(f"Skipping already processed URL: {current_url}")
                continue
            
            # Fetch and process URL
            html = await self.fetch_url(current_url)
            if not html:
                logger.error(f"Failed to fetch content from {current_url}")
                continue
            
            # Extract links
            links = self._extract_links(html, current_url)
            
            # Mark as processed
            self.processed_urls.add(current_url)
            logger.info(f"Successfully processed {current_url}")
            
            # Handle recursive crawling
            if recursive and depth < max_depth:
                new_depth = depth + 1
                logger.info(f"Adding {len(links)} links at depth {new_depth}")
                
                # Add new links to process with incremented depth
                for link in links:
                    if link not in self.processed_urls and link not in [u for u, _ in urls_to_process]:
                        urls_to_process.append((link, new_depth))
                        logger.info(f"Added to processing queue: {link}")
                    else:
                        logger.info(f"Skipping already queued/processed link: {link}")
        
        # Return results
        return {
            "urls_processed": len(self.processed_urls),
            "urls_list": list(self.processed_urls)
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

async def main():
    """Main function to run the crawler test"""
    logger.info("Starting crawler test")
    
    # URL to test
    url = "https://developer.bill.com/docs/home"
    recursive = True
    max_depth = 2
    
    logger.info(f"Testing crawler with URL: {url}, recursive: {recursive}, max_depth: {max_depth}")
    
    # Create crawler instance
    crawler = SimpleCrawler()
    try:
        # Process the URL and print results
        result = await crawler.crawl(
            url=url,
            recursive=recursive,
            max_depth=max_depth
        )
        
        logger.info("Crawl completed successfully")
        logger.info(f"URLs processed: {len(result['urls_list'])}")
        
        if result['urls_list']:
            logger.info("Processed URLs:")
            for i, url in enumerate(result['urls_list'], 1):
                logger.info(f"  {i}. {url}")
        else:
            logger.warning("No URLs were processed!")
    finally:
        await crawler.close()
    
    logger.info("Crawler test completed")

if __name__ == "__main__":
    asyncio.run(main())
