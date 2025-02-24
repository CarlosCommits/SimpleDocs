import { ChildProcess, spawn } from 'child_process';
import fetch from 'node-fetch';

export interface ServerConfig {
    pythonPath?: string;
    apiPort?: number;
    maxRetries?: number;
    healthCheckInterval?: number;
    workingDir?: string;
}

export class FastAPIServer {
    private process: ChildProcess | null = null;
    private port: number;
    private pythonPath: string;
    private maxRetries: number;
    private healthCheckInterval: number;
    private workingDir: string;
    private retryCount: number = 0;
    private healthCheckTimer: NodeJS.Timeout | null = null;

    constructor(config: ServerConfig = {}) {
        this.port = config.apiPort || 8000;
        this.pythonPath = config.pythonPath || 'python';
        this.maxRetries = config.maxRetries || 3;
        this.healthCheckInterval = config.healthCheckInterval || 30000; // 30 seconds
        this.workingDir = config.workingDir || 'C:/Users/Carlos/Desktop/SimpleDocs/docs-crawler';
    }

    async start(): Promise<void> {
        if (this.isRunning()) {
            console.error('FastAPI server is already running');
            return;
        }

        try {
            // Start FastAPI server
            this.process = spawn(this.pythonPath, [
                '-m', 'uvicorn',
                '--app-dir', this.workingDir,
                '--reload',
                'api.main:app',
                '--port', this.port.toString(),
                '--log-level', 'error'
            ], {
                stdio: 'pipe',
                env: {
                    ...process.env,
                    PYTHONPATH: this.workingDir
                },
                cwd: this.workingDir
            });

            // Handle process events
            this.process.on('error', this.handleProcessError.bind(this));
            this.process.on('exit', this.handleProcessExit.bind(this));

            // Log output
            this.process.stdout?.on('data', (data) => {
                console.error(`[FastAPI] ${data.toString().trim()}`);
            });
            this.process.stderr?.on('data', (data) => {
                console.error(`[FastAPI Error] ${data.toString().trim()}`);
            });

            // Wait for server to be ready
            await this.waitForReady();

            // Start health checks
            this.startHealthChecks();

            console.error('FastAPI server started successfully');
        } catch (error) {
            console.error('Failed to start FastAPI server:', error);
            throw error;
        }
    }

    async stop(): Promise<void> {
        if (this.healthCheckTimer) {
            clearInterval(this.healthCheckTimer);
            this.healthCheckTimer = null;
        }

        if (this.process) {
            this.process.kill();
            this.process = null;
            this.retryCount = 0;
            console.error('FastAPI server stopped');
        }
    }

    isRunning(): boolean {
        return this.process !== null && !this.process.killed;
    }

    private async waitForReady(): Promise<void> {
        const maxAttempts = 30; // 3 seconds total
        let attempts = 0;

        while (attempts < maxAttempts) {
            try {
                const response = await fetch(`http://localhost:${this.port}/health`);
                if (response.ok) {
                    return;
                }
            } catch {
                // Ignore errors and keep trying
            }

            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        throw new Error('FastAPI server failed to start');
    }

    private startHealthChecks(): void {
        if (this.healthCheckTimer) {
            clearInterval(this.healthCheckTimer);
        }

        this.healthCheckTimer = setInterval(async () => {
            try {
                const healthy = await this.checkHealth();
                if (!healthy && this.retryCount < this.maxRetries) {
                    console.error('FastAPI server unhealthy, attempting restart');
                    await this.restart();
                }
            } catch (error) {
                console.error('Health check failed:', error);
            }
        }, this.healthCheckInterval);
    }

    private async checkHealth(): Promise<boolean> {
        try {
            const response = await fetch(`http://localhost:${this.port}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }

    private async restart(): Promise<void> {
        this.retryCount++;
        await this.stop();
        await this.start();
    }

    private handleProcessError(error: Error): void {
        console.error('FastAPI server process error:', error);
        this.restart().catch(console.error);
    }

    private handleProcessExit(code: number | null): void {
        console.error(`FastAPI server exited with code ${code}`);
        if (code !== 0 && this.retryCount < this.maxRetries) {
            this.restart().catch(console.error);
        }
    }
}
