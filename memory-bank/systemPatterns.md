# System Architecture & Patterns

## High-Level Architecture
```
MCP Server (Node.js) -> FastAPI Server Manager -> FastAPI Backend -> Supabase/pgvector
```

## Core Components

### 1. MCP Server (Node.js)
- TypeScript implementation
- Manages FastAPI server lifecycle
- Handles user interactions
- Provides tools for documentation management:
  - fetchDocumentation: Crawl and index docs
  - searchDocumentation: Search with source filtering
  - listSources: Overview of available documentation

### 2. FastAPI Server Manager
```typescript
class FastAPIServer {
  private process: ChildProcess | null;
  private port: number;
  
  // Lifecycle Management
  async start(): Promise<void> {
    this.process = spawn(this.pythonPath, [
      '-m', 'uvicorn',
      'api.main:app',
      '--port', this.port.toString()
    ], {
      stdio: 'pipe',
      env: process.env,
      cwd: 'C:/Users/Carlos/Desktop/SimpleDocs/docs-crawler'  // Working directory
    });
  }
  
  async stop(): Promise<void>;
  isRunning(): boolean;
  
  // Health Checks
  async checkHealth(): Promise<boolean>;
  private async waitForReady(): Promise<void>;
  
  // Error Handling
  private handleProcessError(error: Error): void;
  private handleProcessExit(code: number): void;
}
```

### 3. FastAPI Backend
- Python-based REST API
- Handles crawling and content processing
- Manages embeddings generation
- Implements rate limiting and batching

### 4. Database (Supabase/pgvector)
- Document storage in PostgreSQL
- Vector embeddings using pgvector
- Schema and functions (see below)

## Key Technical Patterns

### 1. Server Lifecycle Management
- Auto-start FastAPI when needed
- Process monitoring and health checks
- Graceful shutdown handling
- Error recovery and restarts
- Working directory management

### 2. Process Communication
- HTTP for API requests
- Process signals for lifecycle events
- Environment variables for configuration
- Health check endpoints

### 3. Configuration Management
```typescript
interface ServerConfig {
  pythonPath: string;    // Path to Python interpreter
  apiPort: number;       // FastAPI port
  autoStart: boolean;    // Enable auto-starting
  maxRetries: number;    // Restart attempts
  healthCheckInterval: number;  // MS between checks
  workingDir: string;    // FastAPI working directory
}
```

### 4. Error Handling Strategy
1. Process Level:
   - Crash detection
   - Auto-restart
   - Max retry limits
   - Module import errors
   
2. Request Level:
   - Timeout handling
   - Retry with backoff
   - Circuit breaking

### 5. Health Monitoring
1. Process Health:
   - PID monitoring
   - Memory usage
   - CPU utilization
   - Module imports
   
2. API Health:
   - HTTP health checks
   - Response timing
   - Error rates

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
- Lazy server startup
- Connection pooling
- Process reuse
- Memory management
- Health monitoring
- Working directory setup

## Security Patterns
- Process isolation
- Environment variables
- Port restrictions
- Error sanitization
- Directory access control

## Deployment Configuration
```json
{
  "mcpServers": {
    "docs-crawler": {
      "command": "node",
      "args": ["build/index.js"],
      "env": {
        "AUTO_START_API": "true",
        "PYTHON_PATH": "./venv/Scripts/python",
        "API_PORT": "8000",
        "WORKING_DIR": "C:/Users/Carlos/Desktop/SimpleDocs/docs-crawler"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
