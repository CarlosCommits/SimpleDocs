# SimpleDocs

A powerful documentation search engine that helps you find relevant information across documentation sites. Built with FastAPI and Node.js, it leverages trafilatura for superior content extraction and pgvector for semantic search.

## Architecture

The system consists of two main components:

1. FastAPI Backend Server
   - Handles content crawling and extraction
   - Manages vector embeddings and search
   - Must be running for tools to work

2. MCP Server
   - Provides Cline integration
   - Handles tool requests
   - Forwards requests to FastAPI

## Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL with pgvector extension
- Supabase project (for vector storage)

## Installation

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd SimpleDocs
   ```

2. Set up Python environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. Set up Node.js dependencies:
   ```bash
   cd mcp
   npm install
   npm run build
   ```

4. Configure environment variables:
   ```bash
   # Create .env file in project directory
   cp .env.example .env
   
   # Required variables:
   OPENAI_API_KEY=your-key-here
   SUPABASE_URL=your-url-here
   SUPABASE_KEY=your-key-here
   ```

## Running the Servers

IMPORTANT: The FastAPI server must be started BEFORE using any MCP tools.

1. Start FastAPI Server:
   ```bash
   # In project root directory
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   python -m uvicorn api.main:app --port 8000
   ```

2. Enable MCP Server in Cline:
   - Open Cline
   - Go to MCP Servers
   - Enable "simpledocs"

## Available Tools

1. `fetchDocumentation`
   - Crawl and index documentation from a URL
   - Parameters:
     - url: Documentation URL to crawl
     - recursive: Crawl linked pages (default: true)
     - maxDepth: How deep to crawl (default: 2)

2. `searchDocumentation`
   - Search through indexed documentation
   - Parameters:
     - query: Search query
     - limit: Max results (default: 5)
     - minScore: Minimum similarity (default: 0.5)

3. `listSources`
   - List all indexed documentation sources

## Usage Example

```typescript
// Crawl documentation
Use the fetchDocumentation tool to crawl https://docs.example.com

// Search content
Use the searchDocumentation tool to search for "authentication"

// List sources
Use the listSources tool to see indexed documentation
```

## Troubleshooting

1. Tool Timeouts
   - Verify FastAPI server is running at http://localhost:8000
   - Check FastAPI server logs for errors
   - Ensure all environment variables are set

2. Crawling Issues
   - Check URL is accessible
   - Verify recursive and maxDepth settings
   - Look for rate limiting messages

3. Search Problems
   - Ensure content has been crawled first
   - Check Supabase connection
   - Verify embeddings are being generated

## Development

- FastAPI server: `api/`
  - Content extraction (trafilatura)
  - Vector embeddings
  - Search functionality

- MCP server: `mcp/`
  - Tool definitions
  - Request handling
  - Error management

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Submit a pull request

## License

[Your chosen license]
