import os
from typing import Dict, List, Optional
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urlparse

class SupabaseClient:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required")
            
        self.client: Client = create_client(url, key)

        # Ensure the vector extension and table exist
        self._init_database()

    def _init_database(self):
        """Initialize database with required extensions and tables"""
        # Note: These operations require superuser privileges
        # We assume they've been run manually or through migration
        """
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS documents (
            id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
            url TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            embedding vector(1536),
            source_domain TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            doc_section TEXT,
            parent_url TEXT,
            created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
            updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
        );

        CREATE INDEX IF NOT EXISTS documents_embedding_idx 
        ON documents 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);

        CREATE INDEX IF NOT EXISTS idx_documents_source_domain 
        ON documents(source_domain);
        """
        pass

    def _extract_metadata(self, url: str) -> Dict[str, str]:
        """Extract metadata from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path.lower()
        
        # Determine doc_type based on URL pattern
        doc_type = 'other'
        if '/api/' in path or '/reference/' in path:
            doc_type = 'api'
        elif '/guide/' in path or '/docs/' in path:
            doc_type = 'guide'
        elif '/tutorial/' in path:
            doc_type = 'tutorial'
            
        # Try to determine section from path
        sections = [s for s in path.split('/') if s and s not in ['api', 'docs', 'guide', 'reference']]
        doc_section = sections[-1] if sections else None
        
        return {
            "source_domain": domain,
            "doc_type": doc_type,
            "doc_section": doc_section
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def store_document(self, document: Dict) -> Dict:
        """
        Store a document with its embedding and metadata, updating if it already exists
        Returns a dict with status information: {'success': bool, 'is_new': bool}
        """
        try:
            # Get the URL to use for metadata extraction
            # If this is a chunk, use the original URL for metadata extraction if available
            metadata_url = document.get("original_url", document["url"])
            
            # Extract metadata from URL
            metadata = self._extract_metadata(metadata_url)
            
            # Check if document exists and if content has changed
            existing_doc = self.client.table('documents').select('content').eq('url', document["url"]).execute()
            
            # If document exists and content hasn't changed, skip update
            if existing_doc.data and existing_doc.data[0]['content'] == document["content"]:
                return {"success": True, "is_new": False, "is_updated": False}
            
            # If document exists but content has changed, or document doesn't exist
            doc_data = {
                "url": document["url"],  # This may include the chunk identifier
                "title": document.get("title"),
                "content": document["content"],
                "embedding": document["embedding"],
                "source_domain": metadata["source_domain"],
                "doc_type": metadata["doc_type"],
                "doc_section": metadata["doc_section"],
                "parent_url": document.get("parent_url"),
                "updated_at": "now()"  # Explicitly update the timestamp
            }
            
            # Use upsert operation with URL as the unique key
            response = self.client.table('documents').upsert(
                doc_data,
                on_conflict="url"
            ).execute()
            
            is_new = not existing_doc.data
            
            return {
                "success": True if response.data else False,
                "is_new": is_new,
                "is_updated": not is_new
            }
        except Exception as e:
            print(f"Error storing document: {str(e)}")
            return {"success": False, "is_new": False, "is_updated": False}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def search_documents(
        self,
        embedding: List[float],
        source_domain: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[Dict]:
        """
        Search documents using vector similarity
        """
        try:
            if source_domain:
                # Use source-specific search function
                response = self.client.rpc(
                    'search_source_documents',
                    {
                        'query_embedding': embedding,
                        'source': source_domain,
                        'match_threshold': min_score,
                        'match_count': limit
                    }
                ).execute()
            else:
                # Use general search across all sources
                response = self.client.rpc(
                    'match_documents',
                    {
                        'query_embedding': embedding,
                        'match_threshold': min_score,
                        'match_count': limit
                    }
                ).execute()

            return response.data if response.data else []
        except Exception as e:
            print(f"Error searching documents: {str(e)}")
            return []

    async def get_stats(self) -> Dict:
        """
        Get statistics about stored documents
        """
        try:
            response = self.client.rpc('get_source_stats').execute()
            
            return {
                "sources": response.data if response.data else [],
                "total_sources": len(response.data) if response.data else 0
            }
        except Exception as e:
            print(f"Error getting stats: {str(e)}")
            return {
                "sources": [],
                "total_sources": 0
            }
