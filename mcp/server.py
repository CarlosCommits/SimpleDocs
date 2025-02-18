#!/usr/bin/env python3
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import httpx
import asyncio
import json
from datetime import datetime

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
        "httpx",
        "pydantic"
    ]
)

# API client setup
class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=300.0)
    
    async def check_health(self) -> bool:
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def fetch_documentation(self, request: FetchRequest, ctx: Context) -> str:
        response = await self.client.post(
            "/crawl",
            json={
                "url": str(request.url),
                "recursive": request.recursive,
                "max_depth": request.max_depth
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
            
        data = response.json()
        
        # Report progress if available
        if "chunks_processed" in data and "chunks_total" in data:
            await ctx.report_progress(
                current=data["chunks_processed"],
                total=data["chunks_total"],
                detail=f"URLs: {data['urls_processed']}/{data['urls_discovered']}"
            )
            
        return json.dumps(data, indent=2)
    
    async def search_documentation(self, request: SearchRequest) -> List[DocumentResult]:
        response = await self.client.get(
            "/search",
            params={
                "query": request.query,
                "limit": request.limit,
                "min_score": request.min_score
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
            
        return [DocumentResult(**result) for result in response.json()["results"]]
    
    async def list_sources(self) -> str:
        response = await self.client.get("/search/stats")
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
            
        return json.dumps(response.json(), indent=2)

# Initialize API client
api_client = APIClient()

@mcp.tool()
async def fetch_documentation(
    url: str,
    recursive: bool = True,
    max_depth: int = 2,
    ctx: Context = None
) -> str:
    """Fetch and index documentation from a URL"""
    if not await api_client.check_health():
        raise Exception(
            "FastAPI server is not running. Please start it first:\n\n"
            "1. Open a terminal in the SimpleDocs directory\n"
            "2. Activate Python environment:\n"
            "   .\\venv\\Scripts\\activate  # on Windows\n"
            "3. Start FastAPI server:\n"
            "   python -m uvicorn api.main:app --port 8000\n\n"
            "See README.md for more details."
        )
    
    request = FetchRequest(url=url, recursive=recursive, max_depth=max_depth)
    result = await api_client.fetch_documentation(request, ctx)
    
    return result

@mcp.tool()
async def search_documentation(
    query: str,
    limit: int = 5,
    min_score: float = 0.5
) -> str:
    """Search through indexed documentation"""
    if not await api_client.check_health():
        raise Exception("FastAPI server is not running")
    
    request = SearchRequest(query=query, limit=limit, min_score=min_score)
    results = await api_client.search_documentation(request)
    
    if not results:
        return "No matching documentation found."
    
    formatted_results = []
    for i, result in enumerate(results, 1):
        formatted_results.append(
            f"{i}. [Score: {result.score:.2f}]\n"
            f"{result.content}\n"
            f"Source: {result.url}\n"
        )
    
    return f"Found {len(results)} results:\n\n" + "\n".join(formatted_results)

@mcp.tool()
async def list_sources() -> str:
    """List all documentation sources that have been scraped"""
    if not await api_client.check_health():
        raise Exception("FastAPI server is not running")
    
    return await api_client.list_sources()

if __name__ == "__main__":
    mcp.run()
