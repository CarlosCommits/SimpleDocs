import os
from typing import Optional, List
from openai import OpenAI, OpenAIError
from tenacity import retry, stop_after_attempt, wait_exponential

# Initialize OpenAI client with error handling
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

try:
    client = OpenAI(api_key=api_key)
except Exception as e:
    raise RuntimeError(f"Failed to initialize OpenAI client: {str(e)}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def generate_embeddings(text: str) -> Optional[List[float]]:
    """
    Generate embeddings for text using OpenAI's API
    """
    try:
        # Clean and prepare text
        text = text.replace("\n", " ").strip()
        if not text:
            print("Warning: Empty text provided for embedding generation")
            return None

        # Generate embedding
        print(f"Generating embedding for text of length {len(text)}")
        try:
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            
            # Extract and validate the embedding vector
            if not response.data or not response.data[0].embedding:
                print("Error: No embedding data in response")
                return None
                
            embedding = response.data[0].embedding
            
            # Basic validation of embedding dimensions
            if len(embedding) != 1536:  # OpenAI's text-embedding-ada-002 produces 1536-dimensional vectors
                print(f"Error: Unexpected embedding dimension: {len(embedding)}")
                return None
                
            print(f"Successfully generated embedding of dimension {len(embedding)}")
            return embedding
            
        except OpenAIError as e:
            print(f"OpenAI API Error: {str(e)}")
            if hasattr(e, 'response'):
                print(f"API Response: {e.response}")
            return None
            
    except Exception as e:
        print(f"Unexpected error generating embedding: {str(e)}")
        return None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts in a single API call
    This is much more efficient than making separate calls for each text
    """
    if not texts:
        return []
        
    try:
        # Clean and prepare texts
        cleaned_texts = [text.replace("\n", " ").strip() for text in texts]
        valid_texts = [text for text in cleaned_texts if text]
        
        if not valid_texts:
            print("Warning: No valid texts provided for batch embedding generation")
            return [None] * len(texts)
            
        # Generate embeddings in batch
        print(f"Generating embeddings for {len(valid_texts)} texts in batch")
        try:
            response = client.embeddings.create(
                model="text-embedding-ada-002",
                input=valid_texts
            )
            
            # Extract and validate the embedding vectors
            if not response.data:
                print("Error: No embedding data in response")
                return [None] * len(texts)
                
            # Map the embeddings back to the original texts (including None for invalid texts)
            result = []
            valid_idx = 0
            
            for text in cleaned_texts:
                if not text:  # Skip empty texts
                    result.append(None)
                else:
                    embedding = response.data[valid_idx].embedding
                    
                    # Basic validation of embedding dimensions
                    if len(embedding) != 1536:
                        print(f"Error: Unexpected embedding dimension: {len(embedding)}")
                        result.append(None)
                    else:
                        result.append(embedding)
                        
                    valid_idx += 1
            
            print(f"Successfully generated {len(valid_texts)} embeddings in batch")
            return result
            
        except OpenAIError as e:
            print(f"OpenAI API Error in batch embedding: {str(e)}")
            if hasattr(e, 'response'):
                print(f"API Response: {e.response}")
            return [None] * len(texts)
            
    except Exception as e:
        print(f"Unexpected error generating batch embeddings: {str(e)}")
        return [None] * len(texts)

async def generate_search_embedding(query: str) -> Optional[List[float]]:
    """
    Generate embedding for search query
    """
    return await generate_embeddings(query)
