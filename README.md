# SimpleDocs

A powerful documentation search engine that helps you find relevant information across documentation sites. Built with Python and the Model Context Protocol (MCP), it leverages trafilatura for superior content extraction and pgvector for semantic search.

## Architecture

The system consists of a single MCP server that directly integrates:
- Content crawling and extraction
- Vector embeddings generation
- Semantic search functionality
- Supabase storage integration

## Prerequisites

- Python 3.8+
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
   cd mcp
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r ..\requirements.txt
   pip install "mcp[cli]"  # Required for MCP server execution
   ```

3. Configure Cline MCP Settings:
   ```json
   {
     "mcpServers": {
       "simpledocs": {
         "command": "C:/path/to/SimpleDocs/mcp/.venv/Scripts/mcp.exe",
         "args": [
           "run",
           "C:/path/to/SimpleDocs/mcp/server.py"
         ],
         "env": {
           "OPENAI_API_KEY": "your-key-here",
           "SUPABASE_URL": "your-supabase-url",
           "SUPABASE_ANON_KEY": "your-supabase-key",
           "CRAWLER_RATE_LIMIT": "100",
           "WORKING_DIR": "C:/path/to/SimpleDocs/"
         },
         "disabled": false,
         "autoApprove": [
           "fetch_documentation",
           "search_documentation",
           "list_sources"
         ]
       }
     }
   }
   ```

   Replace the paths and environment variables with your own values:
   - Update all paths to match your SimpleDocs installation directory
   - Set your OpenAI API key
   - Set your Supabase URL and anonymous key
   - Optionally adjust the crawler rate limit

## Available Tools

1. `fetch_documentation`
   - Crawl and index documentation from a URL
   - Parameters:
     - url: Documentation URL to crawl
     - recursive: Crawl linked pages (default: true)
     - max_depth: How deep to crawl (default: 2)

2. `search_documentation`
   - Search through indexed documentation
   - Parameters:
     - query: Search query
     - limit: Max results (default: 5)
     - min_score: Minimum similarity (default: 0.5)

3. `list_sources`
   - List all indexed documentation sources

## Usage Example

1. Enable the MCP Server in Cline:
   - Open Cline
   - Click "Configure MCP Servers"
   - Paste the configuration JSON
   - Click "Done"

2. Use the tools:
   ```
   # Crawl documentation
   fetch_documentation https://developer.bill.com/docs/home

   # Search content
   search_documentation "authentication"

   # List sources
   list_sources
   ```

## Troubleshooting

1. MCP Server Issues
   - Verify Python virtual environment is activated
   - Check all required packages are installed
   - Ensure MCP CLI is installed (`pip install "mcp[cli]"`)
   - Verify paths in MCP settings are correct

2. Crawling Issues
   - Check URL is accessible
   - Verify recursive and max_depth settings
   - Look for rate limiting messages
   - Check CRAWLER_RATE_LIMIT setting

3. Search Problems
   - Ensure content has been crawled first
   - Check Supabase connection
   - Verify OpenAI API key is valid
   - Check embeddings are being generated

## Development

The project is organized into services:
- `crawler.py`: Content extraction and crawling
- `embeddings.py`: Vector embedding generation
- `storage.py`: Supabase integration
- `search.py`: Semantic search functionality
- `server.py`: MCP server implementation

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Submit a pull request

## License

[Your chosen license]
