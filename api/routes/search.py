from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from api.services.search import DocumentSearch

router = APIRouter()
search_service = DocumentSearch()

class SearchResult(BaseModel):
    content: str
    url: str
    title: Optional[str]
    score: float  # This is the similarity score from vector comparison
    source_domain: str
    doc_type: str
    doc_section: Optional[str]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str
    source_domain: Optional[str]

class SourceStats(BaseModel):
    source_domain: str
    count: int
    doc_types: List[str]
    last_updated: str

class StatsResponse(BaseModel):
    sources: List[SourceStats]
    total_sources: int

@router.get("/search", response_model=SearchResponse)
async def search_documentation(
    query: str,
    source_domain: Optional[str] = None,
    limit: int = Query(default=5, ge=1, le=20),
    min_score: float = Query(default=0.5, ge=0, le=1)
):
    """
    Search through documentation using semantic search
    """
    try:
        results = await search_service.search(
            query=query,
            source_domain=source_domain,
            limit=limit,
            min_score=min_score
        )
        
        return SearchResponse(
            results=[
                SearchResult(
                    content=result["content"],
                    url=result["url"],
                    title=result.get("title"),
                    score=result["similarity"],  # Using similarity score from vector comparison
                    source_domain=result["source_domain"],
                    doc_type=result["doc_type"],
                    doc_section=result.get("doc_section")
                )
                for result in results
            ],
            total=len(results),
            query=query,
            source_domain=source_domain
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/stats", response_model=StatsResponse)
async def get_search_stats():
    """
    Get statistics about indexed documentation
    """
    try:
        stats = await search_service.get_stats()
        return StatsResponse(
            sources=[
                SourceStats(
                    source_domain=source["source_domain"],
                    count=source["count"],
                    doc_types=source["doc_types"],
                    last_updated=source["last_updated"]
                )
                for source in stats["sources"]
            ],
            total_sources=stats["total_sources"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
