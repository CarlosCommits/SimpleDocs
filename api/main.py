from dotenv import load_dotenv
import os

# Load environment variables at the very start
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Documentation Crawler",
    description="API for crawling and searching documentation using semantic search",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routes after FastAPI initialization
from api.routes import crawl, search

# Register routes
app.include_router(crawl.router, prefix="/api/v1", tags=["crawl"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])

@app.get("/")
async def root():
    return {"status": "ok", "message": "Documentation Crawler API"}

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for server monitoring"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
