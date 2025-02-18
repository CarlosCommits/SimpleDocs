# Technical Context

## Development Environment

### Required Software
- Python 3.8+
- Git
- Virtual Environment Tools

### Key Dependencies

#### Python Packages
- MCP SDK (v1.3.0.dev0): Core MCP functionality
- OpenAI: Embeddings generation
- Supabase: Database client
- Trafilatura: Web crawling and content extraction
- httpx: HTTP client
- beautifulsoup4: HTML parsing
- pydantic: Data validation

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
1. Set up Python virtual environment:
   ```bash
   python -m venv mcp/.venv
   .venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install "mcp>=1.3.0"
   pip install -r requirements.txt
   ```

3. Configure environment variables
4. Test MCP server integration
5. Verify service functionality

## Testing
- Initial test site: https://developer.bill.com/reference/api-reference-overview
- Test crawling and extraction
- Validate search functionality
- Verify MCP tool integration
- Test progress reporting

## Deployment
- Supabase hosted service
- MCP server runs through Python/FastMCP in Cline
- Configuration through Cline MCP settings

## Virtual Environment Setup
- Location: mcp/.venv
- Python version: 3.8+
- Windows-specific paths
- Package isolation
- Dependency management

## Package Management
- MCP SDK from official repository
- Direct service integration
- Version compatibility
- Windows considerations
- Module resolution

## Performance Considerations
- Direct service calls
- Async operations
- Resource management
- Error handling
- Progress reporting

## Integration Challenges
1. Service Migration:
   - Moving services to MCP server
   - Maintaining functionality
   - Error handling
   - Progress reporting

2. Windows Specifics:
   - Path separators
   - Script extensions
   - Permission handling
   - Virtual environment activation

3. Module Resolution:
   - Package locations
   - Import paths
   - Version conflicts
   - Dependency management

## Documentation Resources
- MCP SDK Documentation
- Python Package Index
- Windows Setup Notes
- Virtual Environment Guides
