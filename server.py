#!/usr/bin/env python3
"""
Python MCP Server - Text Utilities Example
A Python implementation of the Model Context Protocol server with text manipulation tools.
"""

import os
import random
import json
import asyncio
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs

from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn

# Import MCP SDK - using the standard mcp package
try:
    from mcp.server import Server
    from mcp.server.sse import SseServerTransport
    from mcp.types import Tool, TextContent, CallToolResult
except ImportError:
    print("Error: mcp package not found. Install it with: pip install mcp")
    raise

# Create the MCP server instance
server = Server(
    name="text-utilities-mcp-python",
    version="1.0.0"
)

# Define tools
TOOLS = [
    Tool(
        name="reverse_text",
        description="Reverses the order of characters in the given text",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to reverse",
                }
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="uppercase_text",
        description="Converts text to uppercase",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to convert to uppercase",
                }
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="lowercase_text",
        description="Converts text to lowercase",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to convert to lowercase",
                }
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="word_count",
        description="Counts the number of words in the given text",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to count words in",
                }
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="character_count",
        description="Counts the number of characters (including spaces) in the given text",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to count characters in",
                }
            },
            "required": ["text"],
        },
    ),
    Tool(
        name="shuffle_text",
        description="Randomly shuffles the characters in the given text",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to shuffle",
                }
            },
            "required": ["text"],
        },
    ),
]

# Register tools/list handler
@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return TOOLS

# Register tools/call handler
@server.call_tool()
async def call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> CallToolResult:
    """Handle tool execution."""
    args = arguments or {}
    
    if name == "reverse_text":
        text = args.get("text", "")
        reversed_text = text[::-1]
        return CallToolResult(
            content=[TextContent(type="text", text=f"Reversed text: {reversed_text}")]
        )
    
    elif name == "uppercase_text":
        text = args.get("text", "")
        uppercased = text.upper()
        return CallToolResult(
            content=[TextContent(type="text", text=f"Uppercase: {uppercased}")]
        )
    
    elif name == "lowercase_text":
        text = args.get("text", "")
        lowercased = text.lower()
        return CallToolResult(
            content=[TextContent(type="text", text=f"Lowercase: {lowercased}")]
        )
    
    elif name == "word_count":
        text = args.get("text", "")
        words = [w for w in text.split() if w]
        count = len(words)
        plural = "s" if count != 1 else ""
        return CallToolResult(
            content=[TextContent(type="text", text=f"Word count: {count} word{plural}")]
        )
    
    elif name == "character_count":
        text = args.get("text", "")
        count = len(text)
        plural = "s" if count != 1 else ""
        return CallToolResult(
            content=[TextContent(type="text", text=f"Character count: {count} character{plural}")]
        )
    
    elif name == "shuffle_text":
        text = args.get("text", "")
        chars = list(text)
        random.shuffle(chars)
        shuffled = "".join(chars)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Shuffled text: {shuffled}")]
        )
    
    else:
        raise ValueError(f"Unknown tool: {name}")

# Create FastAPI app
app = FastAPI(title="Text Utilities MCP Python")

# Store active transports
active_transports: Dict[str, SseServerTransport] = {}

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "name": "text-utilities-mcp-python",
        "version": "1.0.0",
        "tools": [tool.name for tool in TOOLS],
        "activeSessions": len(active_transports)
    }

# SSE endpoint
@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication."""
    print("New SSE connection established")
    
    # Get message endpoint from env or use default
    message_endpoint = os.getenv("MESSAGE_ENDPOINT", "/message")
    
    # If MESSAGE_ENDPOINT is a full URL, extract just the path
    try:
        parsed = urlparse(message_endpoint)
        if parsed.path:
            message_endpoint = parsed.path
        print(f"Using message endpoint: {message_endpoint}")
    except Exception as e:
        print(f"Using message endpoint as-is: {message_endpoint}")
    
    # Create SSE transport
    transport = SseServerTransport(message_endpoint)
    session_id = transport.session_id
    print(f"Session created: {session_id}")
    
    active_transports[session_id] = transport
    
    # Cleanup on disconnect
    async def cleanup():
        if session_id in active_transports:
            del active_transports[session_id]
            print(f"Session closed: {session_id}")
    
    # Connect server to transport
    await server.connect(transport)
    
    # Return SSE stream
    async def event_generator():
        try:
            async for event in transport.stream():
                yield event
        finally:
            await cleanup()
    
    return EventSourceResponse(event_generator())

# Message endpoint
@app.post("/message")
async def message_endpoint(
    request: Request,
    sessionId: str = Query(..., alias="sessionId")
):
    """Message endpoint for handling MCP messages."""
    print(f"[MESSAGE] Received POST request with sessionId: {sessionId}")
    print(f"[MESSAGE] Active sessions: {', '.join(active_transports.keys())}")
    
    transport = active_transports.get(sessionId)
    
    if not transport:
        print(f"[MESSAGE] Session not found: {sessionId}")
        return JSONResponse(
            status_code=400,
            content={"error": "No active session found"}
        )
    
    print(f"[MESSAGE] Session found, processing message for: {sessionId}")
    
    try:
        body = await request.json()
        response = await transport.handle_post_message(body)
        return JSONResponse(content=response)
    except Exception as error:
        print(f"Error handling message: {error}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

# Start the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    print(f"Text Utilities MCP Python running on port {port}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"SSE endpoint: http://localhost:{port}/sse")
    print(f"Available tools: {', '.join([tool.name for tool in TOOLS])}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
