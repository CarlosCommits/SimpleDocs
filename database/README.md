# Database Documentation

## Overview
The database uses PostgreSQL with the `pgvector` extension for vector similarity search. It stores documentation content, embeddings, and source metadata to enable both source-specific and general semantic search capabilities.

## Schema

### Documents Table
The main table storing all documentation content and metadata:

```sql
documents (
    id uuid PRIMARY KEY,           -- Unique identifier
    url TEXT NOT NULL,            -- Source URL of the document
    title TEXT,                   -- Document title
    content TEXT NOT NULL,        -- Document content
    embedding vector(1536),       -- OpenAI embedding vector
    source_domain TEXT NOT NULL,  -- e.g., 'bill.com', 'stripe.com'
    doc_type TEXT NOT NULL,       -- e.g., 'api', 'guide', 'reference'
    doc_section TEXT,             -- e.g., 'authentication', 'endpoints'
    parent_url TEXT,              -- For hierarchical relationships
    created_at TIMESTAMPTZ,       -- Creation timestamp
    updated_at TIMESTAMPTZ        -- Last update timestamp
)
```

### Indexes
- `documents_embedding_idx`: IVFFlat index for vector similarity search
- `idx_documents_source_domain`: B-tree index for source filtering

## Database Functions

### 1. Source Statistics
```sql
get_source_stats()
```
Returns statistics about indexed documentation sources:
- source_domain: Domain name
- count: Number of documents
- doc_types: Array of unique document types
- last_updated: Latest update timestamp

### 2. Source-Specific Search
```sql
search_source_documents(
    query_embedding vector(1536),
    source text,
    match_threshold float,
    match_count int
)
```
Searches within a specific documentation source:
- query_embedding: Vector representation of search query
- source: Source domain to search within
- match_threshold: Minimum similarity score (0-1)
- match_count: Maximum number of results

### 3. General Search
```sql
match_documents(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
```
Searches across all documentation sources:
- query_embedding: Vector representation of search query
- match_threshold: Minimum similarity score (0-1)
- match_count: Maximum number of results

## Vector Similarity Search
- Uses cosine similarity: `1 - (vector1 <=> vector2)`
- Score range: 0 (dissimilar) to 1 (identical)
- Default threshold: 0.5
- IVFFlat index for efficient similarity search

## Example Queries

### Get Source Statistics
```sql
SELECT * FROM get_source_stats();
```

### Search Within Source
```sql
SELECT * FROM search_source_documents(
    '[0.1, 0.2, ...]'::vector(1536),
    'developer.bill.com',
    0.5,
    5
);
```

### Search All Sources
```sql
SELECT * FROM match_documents(
    '[0.1, 0.2, ...]'::vector(1536),
    0.5,
    5
);
```

## Setup Instructions

1. Enable vector extension:
```sql
CREATE EXTENSION vector;
```

2. Create schema:
```sql
\i schema.sql
```

## Notes
- Vector dimension (1536) matches OpenAI's text-embedding-ada-002 model
- IVFFlat index configured with 100 lists for optimal performance
- Source domain indexing enables efficient source-specific queries
- All timestamps stored in UTC
