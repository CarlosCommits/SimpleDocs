# Technical Context

## Development Environment

### Required Software
- Python 3.8+
- Node.js 16+
- Git

### Key Dependencies

#### Python Packages
- FastAPI: Web framework
- Trafilatura: Web crawling and content extraction
- OpenAI: Embeddings generation
- Supabase: Database client
- uvicorn: ASGI server
- pydantic: Data validation
- httpx: HTTP client
- beautifulsoup4: HTML parsing

#### Node.js Packages
- @modelcontextprotocol/sdk: MCP server implementation
- typescript: Programming language
- supabase-js: Supabase client

### Environment Variables
```
OPENAI_API_KEY=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
SUPABASE_URL=https://ooupqwxqqibopnfmvicb.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vdXBxd3hxcWlib3BuZm12aWNiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzkzOTM1NTksImV4cCI6MjA1NDk2OTU1OX0.byqXxqxA5IyCKAZxPwQzlavjC3PnpTnsvvy6XlIeGAg
CRAWLER_RATE_LIMIT=100
```

## External Services

### Supabase
- Project URL: https://ooupqwxqqibopnfmvicb.supabase.co
- Features used:
  - PostgreSQL database
  - pgvector extension
  - REST API

### OpenAI
- Model: text-embedding-ada-002
- Vector size: 1536
- Used for generating embeddings

## Development Workflow
1. Set up Python virtual environment
2. Install Python dependencies
3. Install Node.js dependencies
4. Configure environment variables
5. Run FastAPI development server
6. Run MCP server

## Testing
- Initial test site: https://developer.bill.com/reference/api-reference-overview
- Test crawling and extraction
- Validate search functionality
- Verify MCP tool integration

## Deployment
- FastAPI server runs locally
- Supabase hosted service
- MCP server runs as local process
