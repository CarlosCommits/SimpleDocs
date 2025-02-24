#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from '@modelcontextprotocol/sdk/types.js';
import axios, { AxiosInstance } from 'axios';
import dotenv from 'dotenv';
import { FastAPIServer, ServerConfig } from './server.js';
import { exec } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Load environment variables
dotenv.config({ path: '../.env' });

const API_PORT = parseInt(process.env.API_PORT || '8000');
const API_BASE_URL = `http://localhost:${API_PORT}/api/v1`;

const serverConfig: ServerConfig = {
  pythonPath: process.env.PYTHON_PATH,
  apiPort: API_PORT,
  maxRetries: 3,
  healthCheckInterval: 30000,
  workingDir: process.env.WORKING_DIR || 'C:/Users/Carlos/Desktop/SimpleDocs'
};

interface FetchRequest {
  url: string;
  recursive?: boolean;
  maxDepth?: number;
}

interface SearchRequest {
  query: string;
  limit?: number;
  minScore?: number;
}

interface DocumentResult {
  content: string;
  url: string;
  title?: string;
  score: number;
}

class SimpledocsServer {
  private server: Server;
  private apiClient: AxiosInstance;
  private apiServer: FastAPIServer;
  private workingDir: string;

  constructor() {
    this.workingDir = process.env.WORKING_DIR || 'C:/Users/Carlos/Desktop/SimpleDocs';
    // Initialize FastAPI server manager
    this.apiServer = new FastAPIServer(serverConfig);
    this.server = new Server(
      {
        name: 'simpledocs',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.apiClient = axios.create({
      baseURL: API_BASE_URL,
      timeout: 300000, // 5 minutes
    });

    this.setupErrorHandling();
    this.setupToolHandlers();
  }

  private setupErrorHandling() {
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    
    // Handle all exit cases
    process.on('SIGINT', this.handleExit.bind(this));   // Ctrl+C
    process.on('SIGTERM', this.handleExit.bind(this));  // Kill
    process.on('exit', this.cleanup.bind(this));        // Normal exit
    process.on('disconnect', this.handleExit.bind(this)); // Parent process dies
    
    // Handle uncaught errors
    process.on('uncaughtException', async (error) => {
      console.error('Uncaught error:', error);
      await this.handleExit();
    });
  }

  private async handleExit() {
    console.error('Shutting down servers...');
    await this.cleanup();
    process.exit(0);
  }

  private async cleanup() {
    if (this.apiServer) {
      console.error('[FastAPI] Stopping server...');
      await this.apiServer.stop();
      console.error('[FastAPI] Server stopped');
    }
    if (this.server) {
      await this.server.close();
    }
  }

  private async ensurePythonEnvironment(): Promise<void> {
    const venvPath = path.join(this.workingDir, 'venv');
    const requirementsPath = path.join(this.workingDir, 'requirements.txt');
    
    // Check if environment needs setup
    const needsSetup = !fs.existsSync(venvPath);
    if (needsSetup) {
      console.error(`
[Python] Virtual environment not found
[Python] Setting up environment automatically...`);
      
      try {
        // Create venv
        await execAsync('python -m venv venv', { cwd: this.workingDir });
        
        // Install requirements
        const pythonPath = path.join(venvPath, 'Scripts', 'python.exe');
        await execAsync(`${pythonPath} -m pip install -r requirements.txt`, {
          cwd: this.workingDir
        });
        
        console.error('[Python] Environment setup complete');
      } catch (error: any) {
        throw new McpError(
          ErrorCode.InternalError,
          `Failed to setup Python environment: ${error?.message || String(error)}`
        );
      }
    }
    
    // Verify packages
    try {
      const pythonPath = path.join(venvPath, 'Scripts', 'python.exe');
      await execAsync(`${pythonPath} -c "import trafilatura, httpx, fastapi"`, {
        cwd: this.workingDir
      });
    } catch {
      throw new McpError(
        ErrorCode.InternalError,
        'Failed to verify Python packages. Try removing venv folder and trying again.'
      );
    }
  }

  private async checkApiServer(): Promise<void> {
    try {
      const response = await this.apiClient.get('/health');
      // FastAPI is running
      return;
    } catch {
      throw new McpError(
        ErrorCode.InternalError,
        `FastAPI server is not running. Please start it first:
        
1. Open a terminal in the SimpleDocs directory
2. Activate Python environment:
   source venv/bin/activate  # or .\\venv\\Scripts\\activate on Windows
3. Start FastAPI server:
   python -m uvicorn api.main:app --port 8000
        
See README.md for more details.`
      );
    }
  }

  private async withApiConnection<T>(
    toolName: string,
    action: () => Promise<T>
  ): Promise<T> {
    await this.checkApiServer();
    return action();
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'fetchDocumentation',
          description: 'Fetch and index documentation from a URL',
          inputSchema: {
            type: 'object',
            properties: {
              url: {
                type: 'string',
                description: 'URL of the documentation to fetch',
              },
              recursive: {
                type: 'boolean',
                description: 'Whether to recursively crawl links (defaults to true)',
                default: true,
              },
              maxDepth: {
                type: 'number',
                description: 'Maximum depth for recursive crawling (0: just the URL, 1: +linked pages, 2: +subpages)',
                default: 2,
              },
            },
            required: ['url'],
          },
        },
        {
          name: 'searchDocumentation',
          description: 'Search through indexed documentation',
          inputSchema: {
            type: 'object',
            properties: {
              query: {
                type: 'string',
                description: 'Search query',
              },
              limit: {
                type: 'number',
                description: 'Maximum number of results',
                default: 5,
              },
              minScore: {
                type: 'number',
                description: 'Minimum similarity score (0-1)',
                default: 0.5,
              },
            },
            required: ['query'],
          },
        },
        {
          name: 'listSources',
          description: 'List all documentation sources that have been scraped',
          inputSchema: {
            type: 'object',
            properties: {},
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      switch (request.params.name) {
        case 'fetchDocumentation':
          return this.handleFetchDocumentation(request.params.arguments);
        case 'searchDocumentation':
          return this.handleSearchDocumentation(request.params.arguments);
        case 'listSources':
          return this.handleListSources();
        default:
          throw new McpError(
            ErrorCode.MethodNotFound,
            `Unknown tool: ${request.params.name}`
          );
      }
    });
  }

  private async handleFetchDocumentation(args: any) {
    if (!args.url || typeof args.url !== 'string') {
      throw new McpError(ErrorCode.InvalidParams, 'URL is required');
    }

    return this.withApiConnection('fetchDocumentation', async () => {
      // Apply defaults for recursive crawling
      const requestBody = {
        url: args.url,
        recursive: args.recursive ?? true,  // Default to true if not provided
        max_depth: args.maxDepth ?? 2      // Default to 2 if not provided
      };
      
      let lastProgress: any = null;
      const response = await this.apiClient.post('/crawl', requestBody, {
        responseType: 'text',
        transformResponse: (data) => data,
        onDownloadProgress: (progressEvent: any) => {
          try {
            const text = progressEvent.event.target.responseText;
            const lines = text.split('\n').filter((line: string) => line.startsWith('data: '));
            
            if (lines.length > 0) {
              // Get latest progress
              const progress = JSON.parse(lines[lines.length - 1].slice(6));
              lastProgress = progress;
              
              if (progress.status === 'processing') {
                return {
                  content: [{
                    type: 'progress',
                    text: 'Processing documentation...',
                    current: progress.chunks_processed,
                    total: progress.chunks_total || 1,
                    detail: `URLs: ${progress.urls_processed}/${progress.urls_discovered}`
                  }]
                };
              }
            }
          } catch (error) {
            console.error('Error parsing progress:', error);
          }
        }
      });

      // Return final summary
      if (lastProgress && lastProgress.status === 'complete') {
        return {
          content: [{
            type: 'text',
            text: [
              `Documentation Crawl Complete!`,
              ``,
              `📊 Progress Summary:`,
              `URLs Processed: ${lastProgress.urls_processed}/${lastProgress.urls_discovered}`,
              `Content Chunks: ${lastProgress.chunks_processed}/${lastProgress.chunks_total}`,
              ``,
              `🌐 Processed URLs:`,
              ...lastProgress.urls_list.map((url: string) => `- ${url}`)
            ].join('\n')
          }]
        };
      }

      return {
        content: [{
          type: 'text',
          text: 'Documentation crawl completed with unknown status.'
        }]
      };
    });
  }

  private async handleSearchDocumentation(args: any) {
    if (!args.query || typeof args.query !== 'string') {
      throw new McpError(ErrorCode.InvalidParams, 'Query is required');
    }

    return this.withApiConnection('searchDocumentation', async () => {
      const response = await this.apiClient.get('/search', {
        params: {
          query: args.query,
          limit: args.limit,
          min_score: args.minScore,
        },
      });

      const results = response.data.results;
      if (!results.length) {
        return {
          content: [
            {
              type: 'text',
              text: 'No matching documentation found.',
            },
          ],
        };
      }

      return {
        content: [
          {
            type: 'text',
            text: `Found ${results.length} results:\n\n${results
              .map(
                (r: DocumentResult, i: number) =>
                  `${i + 1}. [Score: ${r.score.toFixed(2)}]\n${r.content}\nSource: ${r.url}\n`
              )
              .join('\n')}`,
          },
        ],
      };
    });
  }

  private async handleListSources() {
    return this.withApiConnection('listSources', async () => {
      const response = await this.apiClient.get('/search/stats');
      return {
        content: [
          {
            type: 'text',
            text: `Documentation Sources:\n${JSON.stringify(response.data, null, 2)}`,
          },
        ],
      };
    });
  }

  async run() {
    try {
      const transport = new StdioServerTransport();
      await this.server.connect(transport);
      console.error('Simpledocs MCP server running on stdio');
      console.error('NOTE: FastAPI server must be running for tools to work');
    } catch (error: any) {
      console.error('Failed to start server:', error?.message || String(error));
      await this.handleExit();
    }
  }
}

const server = new SimpledocsServer();
server.run().catch(console.error);
