# Active Development Context

## Current Phase
Progress Streaming Debugging

## Recent Changes
- Attempted streaming implementation
- Added Server-Sent Events
- Updated FastAPI routes
- Modified MCP server response handling
- Fixed hash fragment handling
- Improved URL normalization

## Current Issues
1. Progress Bar Not Working:
   - Timeout still occurring
   - No progress updates showing
   - FastAPI streaming not reaching client

2. Streaming Implementation:
   ```typescript
   // Current approach not working
   responseType: 'text',
   transformResponse: (data) => data,
   onDownloadProgress: (progressEvent: any) => {
     const text = progressEvent.event.target.responseText;
     // Progress updates not reaching here
   }
   ```

3. Possible Problems:
   - Axios streaming configuration
   - Event handling timing
   - Response type mismatch
   - Progress event structure

## Next Attempts
1. Try EventSource:
```typescript
const eventSource = new EventSource('/api/v1/crawl');
eventSource.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  // Handle progress
};
```

2. Or WebSocket:
```typescript
const ws = new WebSocket('ws://localhost:8000/api/v1/crawl');
ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  // Handle progress
};
```

3. Or Chunked Transfer:
```typescript
responseType: 'stream',
headers: {
  'Accept': 'text/event-stream',
  'Cache-Control': 'no-cache'
}
```

## Implementation Status
- [x] Project restructuring
- [x] Path updates
- [x] Documentation updates
- [x] MCP server rebuild
- [x] Package name updates
- [ ] Progress streaming (failed)
- [x] URL normalization
- [x] Timeout configuration
- [ ] Socket management (pending)
- [ ] Process tracking (pending)

## Current Architecture
```
User
  |
  ├── FastAPI Server (Manual Start)
  |     ├── Content Extraction (trafilatura)
  |     ├── Link Processing
  |     |     ├── Hash fragment removal
  |     |     ├── URL normalization
  |     |     └── Duplicate prevention
  |     ├── Progress Streaming (not working)
  |     |     ├── SSE implementation
  |     |     ├── Real-time updates
  |     |     └── Progress tracking
  |     ├── Chunking
  |     └── Vector Storage
  |
  └── MCP Server
        ├── Tool Interface
        ├── Stream Processing (failing)
        |     ├── Event parsing
        |     ├── Progress updates
        |     └── Completion handling
        ├── Request Handling
        └── Error Management
```

## Technical Debt
1. Progress Streaming:
   - Unreliable implementation
   - Timeout issues
   - Missing progress updates

2. Socket Cleanup:
   - Ghost processes in netstat
   - TIME_WAIT states
   - Port blocking

3. Process Management:
   - No process tracking
   - Incomplete cleanup
   - Missing health checks

4. Configuration:
   - Hardcoded port
   - Limited socket options
   - No fallback ports

## Notes
- FastAPI must be running before MCP tools work
- Socket states need better management
- Process cleanup needs improvement
- Consider adding port configuration
- Project structure now cleaner and more maintainable
- Progress reporting needs complete rework
- URL handling improved but untested due to timeouts
