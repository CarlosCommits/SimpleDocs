#!/usr/bin/env python3
from fastmcp import FastMCP, Context
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import json
import os
import asyncio
from datetime import datetime
from services import DocumentCrawler, DocumentSearch

# Pydantic models for request/response
class FetchRequest(BaseModel):
    url: HttpUrl
    recursive: Optional[bool] = True
    max_depth: Optional[int] = 2
    doc_patterns: Optional[List[str]] = None

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 3
    min_score: Optional[float] = 0.81

class DocumentResult(BaseModel):
    content: str
    url: str
    title: Optional[str]
    score: float
    source_domain: str
    doc_type: str
    doc_section: Optional[str]

# FastMCP server setup
mcp = FastMCP(
    "simpledocs",
    dependencies=[
        "openai",
        "supabase",
        "trafilatura",
        "httpx",
        "beautifulsoup4",
        "pydantic"
    ]
)

# Initialize services
search_client = DocumentSearch()

@mcp.tool()
async def fetch_documentation(
    url: str,
    recursive: bool = True,
    max_depth: int = 2,
    doc_patterns: List[str] = None,
    ctx: Context = None
) -> str:
    """Fetch and index documentation from a URL"""
    try:
        # Start the WebSocket server in a separate task
        try:
            from services import websocket_server
            asyncio.create_task(websocket_server.start_server())
        except Exception as e:
            print(f"Warning: Could not start WebSocket server: {str(e)}")
        
        # Create dashboard URL and open in browser
        import webbrowser
        dashboard_url = f"file://{os.path.abspath(os.path.join(os.path.dirname(__file__), 'dashboard', 'index.html'))}"
        print(f"\nOpening Progress Dashboard: {dashboard_url}\n")
        webbrowser.open(dashboard_url)
        
        async with DocumentCrawler() as crawler:
            # Use the crawl method with context for progress reporting
            result = await crawler.crawl(
                url=url,
                recursive=recursive,
                max_depth=max_depth,
                doc_patterns=doc_patterns,
                ctx=ctx
            )
            
            return json.dumps(result, indent=2)
    except Exception as e:
        raise Exception(f"Error fetching documentation: {str(e)}")

@mcp.tool()
async def search_documentation(
    query: str,
    limit: int = 3,
    min_score: float = 0.81
) -> str:
    """Search through indexed documentation"""
    try:
        results = await search_client.search(
            query=query,
            limit=limit,
            min_score=min_score
        )
        if not results:
            return "No matching documentation found."
        formatted_results = [
            f"{i}. [Score: {result['similarity']:.2f}]\n{result['content']}\nSource: {result['url']}\n"
            for i, result in enumerate(results, 1)
        ]
        return f"Found {len(results)} results:\n\n" + "\n".join(formatted_results)
    except Exception as e:
        raise Exception(f"Error searching documentation: {str(e)}")

@mcp.tool()
async def list_sources() -> str:
    """List all documentation sources that have been scraped"""
    try:
        stats = await search_client.get_stats()
        return json.dumps(stats, indent=2)
    except Exception as e:
        raise Exception(f"Error listing sources: {str(e)}")

if __name__ == "__main__":
    mcp.run()
