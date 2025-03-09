#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import signal
import websockets
from typing import Dict, List, Set, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("websocket_server")

# WebSocket server configuration
WS_HOST = "127.0.0.1"
WS_PORT = 8765
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "progress.json")

class ProgressWebSocketServer:
    def __init__(self, host: str = WS_HOST, port: int = WS_PORT):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.current_progress: Dict[str, Any] = {
            "status": "idle",
            "urls_processed": 0,
            "urls_discovered": 0,
            "chunks_processed": 0,
            "chunks_total": 0,
            "current_url": "",
            "urls_list": [],
            "last_updated": datetime.now().isoformat()
        }
        self.server = None
        self._load_progress()
        
    def _load_progress(self) -> None:
        """Load progress from file if it exists"""
        try:
            if os.path.exists(PROGRESS_FILE):
                with open(PROGRESS_FILE, 'r') as f:
                    self.current_progress = json.load(f)
                logger.info(f"Loaded progress from {PROGRESS_FILE}")
        except Exception as e:
            logger.error(f"Error loading progress file: {str(e)}")
            
    def _save_progress(self) -> None:
        """Save progress to file"""
        try:
            # Update timestamp
            self.current_progress["last_updated"] = datetime.now().isoformat()
            
            # Save to file
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(self.current_progress, f, indent=2)
            logger.info(f"Saved progress to {PROGRESS_FILE}")
        except Exception as e:
            logger.error(f"Error saving progress file: {str(e)}")
    
    async def register(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Register a new client"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send current progress to new client
        await websocket.send(json.dumps(self.current_progress))
    
    async def unregister(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Unregister a client"""
        self.clients.remove(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients"""
        if not self.clients:
            return
            
        # Update current progress
        self.current_progress.update(message)
        self.current_progress["last_updated"] = datetime.now().isoformat()
        
        # Save progress to file
        self._save_progress()
        
        # Broadcast to all clients
        websockets_tasks = []
        for client in self.clients:
            websockets_tasks.append(asyncio.create_task(
                client.send(json.dumps(self.current_progress))
            ))
            
        if websockets_tasks:
            await asyncio.gather(*websockets_tasks, return_exceptions=True)
    
    async def update_progress(self, progress: Dict[str, Any]) -> None:
        """Update progress and broadcast to clients"""
        await self.broadcast(progress)
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Handle client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if "type" in data:
                        if data["type"] == "get_progress":
                            # Client requesting current progress
                            await websocket.send(json.dumps(self.current_progress))
                        elif data["type"] == "reset_progress":
                            # Client requesting progress reset
                            self.current_progress = {
                                "status": "idle",
                                "urls_processed": 0,
                                "urls_discovered": 0,
                                "chunks_processed": 0,
                                "chunks_total": 0,
                                "current_url": "",
                                "urls_list": [],
                                "last_updated": datetime.now().isoformat()
                            }
                            self._save_progress()
                            await self.broadcast(self.current_progress)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def start(self) -> None:
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        # Create and start server
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        
        logger.info(f"WebSocket server running at ws://{self.host}:{self.port}")
        
        # Keep server running
        await self.server.wait_closed()
    
    async def stop(self) -> None:
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")

# Singleton instance
_server_instance: Optional[ProgressWebSocketServer] = None

def get_server() -> ProgressWebSocketServer:
    """Get or create the server instance"""
    global _server_instance
    if _server_instance is None:
        _server_instance = ProgressWebSocketServer()
    return _server_instance

async def start_server() -> None:
    """Start the WebSocket server"""
    server = get_server()
    await server.start()

async def stop_server() -> None:
    """Stop the WebSocket server"""
    server = get_server()
    await server.stop()

async def update_progress(progress: Dict[str, Any]) -> None:
    """Update progress"""
    server = get_server()
    await server.update_progress(progress)

# Run server if executed directly
if __name__ == "__main__":
    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    
    async def shutdown(signal, loop):
        """Cleanup tasks tied to the service's shutdown."""
        logger.info(f"Received exit signal {signal.name}...")
        await stop_server()
        
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
    
    # Add signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(s, loop))
        )
    
    # Start server
    try:
        loop.run_until_complete(start_server())
        loop.run_forever()
    finally:
        loop.close()
        logger.info("WebSocket server shutdown complete")
