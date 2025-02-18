# Active Development Context

## Current Phase
Architectural Simplification - Removing FastAPI Dependency

## Recent Changes
- Identified need to simplify architecture by removing FastAPI layer
- Analyzed current implementation and dependencies
- Planned migration of core services to MCP server

## Current Focus
1. Architecture Simplification:
   - Remove FastAPI middleware layer
   - Move core services directly into MCP server
   - Eliminate need for separate server process
   - Maintain existing functionality

2. Core Services Migration:
   - Crawler service
   - Embeddings generation
   - Vector storage
   - Progress tracking

## Next Steps
1. Migrate Core Services:
   - Move crawler implementation to MCP server
   - Integrate embeddings service directly
   - Connect storage service to MCP server
   - Port progress tracking functionality

2. Update Dependencies:
   - Keep essential packages:
     - OpenAI for embeddings
     - Supabase for storage
     - Trafilatura/BeautifulSoup for content
     - HTTPX for requests
   - Remove FastAPI-specific dependencies

3. Implement Direct Service Calls:
   - Update MCP tools to use services directly
   - Maintain existing tool interfaces
   - Ensure proper error handling
   - Preserve progress reporting

## Implementation Status
- [x] Architecture analysis
- [x] Migration planning
- [ ] Core services migration
- [ ] Dependency updates
- [ ] Tool interface updates
- [ ] Testing and validation

## Current Architecture
```
Current:
User -> MCP Server -> FastAPI Server -> Core Services

Planned:
User -> MCP Server -> Core Services
           ├── Crawler Service
           ├── Embeddings Service
           └── Storage Service
```

## Technical Debt
1. Service Integration:
   - Clean migration of services
   - Error handling consistency
   - Progress reporting implementation
   - Resource cleanup

2. Documentation:
   - Update architecture diagrams
   - Document simplified flow
   - Update setup instructions
   - Remove FastAPI references

3. Testing:
   - Verify functionality
   - Performance testing
   - Error scenarios
   - Progress reporting

## Notes
- Simplified architecture will reduce complexity
- Direct service calls will improve performance
- No more need to start/manage FastAPI server
- Maintain same functionality with streamlined implementation
