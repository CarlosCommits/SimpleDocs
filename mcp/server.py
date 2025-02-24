#!/usr/bin/env python3
from fastmcp import FastMCP, Context
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import json
from datetime import datetime
from services import DocumentCrawler, DocumentSearch

# Pydantic models for request/response
class FetchRequest(BaseModel):
    url: HttpUrl
    recursive: Optional[bool] = True
    max_depth: Optional[int] = 2

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    min_score: Optional[float] = 0.5

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
    ctx: Context = None
) -> str:
    """Fetch and index documentation from a URL"""
    try:
        async with DocumentCrawler() as crawler:
            # Use the crawl method which properly handles URL processing
            result = await crawler.crawl(
                url=url,
                recursive=recursive,
                max_depth=max_depth,
                ctx=ctx
            )
            
            return json.dumps(result, indent=2)
    except Exception as e:
        raise Exception(f"Error fetching documentation: {str(e)}")

@mcp.tool()
async def search_documentation(
    query: str,
    limit: int = 5,
    min_score: float = 0.5
) -> str:
    """Search through indexed documentation"""
    try:
        # Search documents using DocumentSearch service
        results = await search_client.search(
            query=query,
            limit=limit,
            min_score=min_score
        )
        
        if not results:
            return "No matching documentation found."
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"{i}. [Score: {result['similarity']:.2f}]\n"
                f"{result['content']}\n"
                f"Source: {result['url']}\n"
            )
        
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
