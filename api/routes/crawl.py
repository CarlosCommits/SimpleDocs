from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from api.services.crawler import DocumentCrawler
import time

router = APIRouter()
crawler = DocumentCrawler()

class CrawlRequest(BaseModel):
    url: HttpUrl
    recursive: Optional[bool] = False
    max_depth: Optional[int] = 1

class CrawlResponse(BaseModel):
    status: str
    message: str
    urls_discovered: int
    urls_processed: int
    chunks_processed: int
    chunks_total: int
    time_elapsed: str
    urls_list: List[str]

@router.post("/crawl")
async def crawl_documentation(request: CrawlRequest):
    """
    Crawl documentation from a specified URL with streaming progress updates
    """
    try:
        async def progress_generator():
            async for progress in crawler.crawl_with_progress(
                str(request.url),
                recursive=request.recursive,
                max_depth=request.max_depth
            ):
                yield f"data: {json.dumps(progress)}\n\n"

        return StreamingResponse(
            progress_generator(),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_crawl_status(job_id: str):
    """
    Get the status of a crawl job
    """
    try:
        status = await crawler.get_status(job_id)
        return {"status": status}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
