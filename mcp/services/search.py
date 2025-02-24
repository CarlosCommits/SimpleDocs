from typing import List, Dict, Optional
from .embeddings import generate_search_embedding
from .storage import SupabaseClient

class DocumentSearch:
    def __init__(self):
        self.supabase = SupabaseClient()

    async def search(
        self,
        query: str,
        source_domain: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.5
    ) -> List[Dict]:
        """
        Search documents using semantic search
        """
        try:
            # Generate embedding for search query
            query_embedding = await generate_search_embedding(query)
            if not query_embedding:
                return []

            # Search documents using vector similarity
            results = await self.supabase.search_documents(
                embedding=query_embedding,
                source_domain=source_domain,
                limit=limit,
                min_score=min_score
            )

            return results
        except Exception as e:
            print(f"Error performing search: {str(e)}")
            return []

    async def get_stats(self) -> Dict:
        """
        Get statistics about indexed documentation
        """
        try:
            return await self.supabase.get_stats()
        except Exception as e:
            print(f"Error getting stats: {str(e)}")
            return {
                "sources": [],
                "total_sources": 0
            }
