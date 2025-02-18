-- Enable vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    embedding vector(1536),
    source_domain TEXT NOT NULL DEFAULT '',
    doc_type TEXT NOT NULL DEFAULT '',
    doc_section TEXT,
    parent_url TEXT,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

-- Create indexes
CREATE INDEX IF NOT EXISTS documents_embedding_idx 
ON documents 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_documents_source_domain 
ON documents(source_domain);

-- Create source statistics function
CREATE OR REPLACE FUNCTION get_source_stats()
RETURNS TABLE (
    source_domain text,
    count bigint,
    doc_types text[],
    last_updated timestamptz
) 
LANGUAGE sql AS $$
    SELECT 
        source_domain,
        count(*) as count,
        array_agg(distinct doc_type) as doc_types,
        max(updated_at) as last_updated
    FROM documents
    GROUP BY source_domain
    ORDER BY count DESC;
$$;

-- Create source-specific search function
CREATE OR REPLACE FUNCTION search_source_documents(
    query_embedding vector(1536),
    source text,
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id uuid,
    url text,
    title text,
    content text,
    source_domain text,
    doc_type text,
    doc_section text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        url,
        title,
        content,
        source_domain,
        doc_type,
        doc_section,
        1 - (documents.embedding <=> query_embedding) as similarity
    FROM documents
    WHERE 
        source_domain = source
        AND 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;

-- Create general search function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id uuid,
    url text,
    title text,
    content text,
    source_domain text,
    doc_type text,
    doc_section text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        url,
        title,
        content,
        source_domain,
        doc_type,
        doc_section,
        1 - (documents.embedding <=> query_embedding) as similarity
    FROM documents
    WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
