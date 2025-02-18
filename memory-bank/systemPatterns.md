# System Architecture & Patterns

## High-Level Architecture
```
MCP Server (Python/FastMCP) -> Supabase/pgvector
```

## Core Components

### 1. MCP Server (Python/FastMCP)
- Python implementation using FastMCP/MCP SDK
- Direct integration of core services:
  - Crawler Service: Web crawling and content extraction
  - Embeddings Service: Vector generation
  - Storage Service: Database operations
- Tools for documentation management:
  - fetchDocumentation: Crawl and index docs
  - searchDocumentation: Search with source filtering
  - listSources: Overview of available documentation
- Built-in progress reporting and context management

### 2. Virtual Environment Setup
```bash
# Create and activate virtual environment
python -m venv mcp/.venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install "mcp>=1.3.0"
pip install -r requirements.txt
```

### 3. Database (Supabase/pgvector)
- Document storage in PostgreSQL
- Vector embeddings using pgvector
- Schema and functions (see below)

## Key Technical Patterns

### 1. Python Environment Management
- Isolated virtual environment
- Package version control
- Dependency management
- Windows-specific considerations

### 2. Service Integration
- Direct service calls
- Async operations
- Progress tracking
- Error handling
- Resource management

### 3. Configuration Management
```python
# MCP SDK configuration
from mcp import MCP

mcp = MCP(
    name="simpledocs",
    dependencies=[
        "openai",
        "supabase",
        "trafilatura",
        "httpx"
    ],
)
```

### 4. Error Handling Strategy
1. Service Level:
   - OpenAI API errors
   - Database connection issues
   - Crawling failures
   - Rate limiting
   
2. Tool Level:
   - Input validation
   - Progress reporting
   - Resource cleanup
   - Error propagation

### 5. Progress Monitoring
1. Crawling Progress:
   - URLs processed
   - Content extraction
   - Embedding generation
   - Storage operations
   
2. Search Progress:
   - Query processing
   - Vector matching
   - Result formatting

## Database Schema
```sql
create table documents (
  id uuid primary key default uuid_generate_v4(),
  url text not null,
  title text,
  content text not null,
  embedding vector(1536),
  source_domain text not null,
  doc_type text not null,
  doc_section text,
  parent_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Indexes
create index idx_documents_source_domain on documents(source_domain);
create index documents_embedding_idx on documents using ivfflat (embedding vector_cosine_ops);

-- Functions
create or replace function get_source_stats() ...
create or replace function search_source_documents() ...
create or replace function match_documents() ...
```

## Performance Considerations
- Direct service integration
- Async operations
- Resource management
- Error handling efficiency
- Progress reporting overhead

## Security Patterns
- API key management
- Database credentials
- Rate limiting
- Input validation
- Error sanitization

## Deployment Configuration
```json
{
  "mcpServers": {
    "simpledocs": {
      "command": "C:/Users/Carlos/Desktop/SimpleDocs/mcp/.venv/Scripts/python.exe",
      "args": [
        "-m",
        "mcp",
        "run",
        "server.py"
      ],
      "env": {
        "OPENAI_API_KEY": "...",
        "SUPABASE_URL": "...",
        "SUPABASE_ANON_KEY": "...",
        "CRAWLER_RATE_LIMIT": "100"
      },
      "disabled": false,
      "autoApprove": ["listSources"]
    }
  }
}
```

## Installation Patterns
1. Virtual Environment:
   ```bash
   python -m venv mcp/.venv
   .venv\Scripts\activate  # Windows
   ```

2. Dependencies:
   ```bash
   pip install "mcp>=1.3.0"
   pip install -r requirements.txt
   ```

3. Configuration:
   - Set up environment variables
   - Configure virtual environment paths
   - Set working directory
   - Configure Cline integration

## Windows-Specific Considerations
1. Path Formatting:
   - Use forward slashes in JSON
   - Use correct venv activation script
   - Handle spaces in paths

2. Virtual Environment:
   - Use Scripts instead of bin
   - Handle path separators
   - Consider permission issues

3. Module Resolution:
   - Package installation location
   - Module import paths
   - System vs user packages
