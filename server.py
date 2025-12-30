#!/usr/bin/env python3
"""
Python MCP Server - Text Utilities Example
A Python implementation of the Model Context Protocol server with text manipulation tools.
Uses a simple HTTP/SSE approach similar to the Node.js MCP SDK pattern.
"""

import os
import random
import json
import uuid
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Query, Response
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import uvicorn

# Create FastAPI app
app = FastAPI(title="Text Utilities MCP Python")

# Store active sessions
active_sessions: Dict[str, asyncio.Queue] = {}

# Define tools
TOOLS = [
    {
        "name": "reverse_text",
        "description": "Reverses the order of characters in the given text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to reverse",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "uppercase_text",
        "description": "Converts text to uppercase",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to convert to uppercase",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "lowercase_text",
        "description": "Converts text to lowercase",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to convert to lowercase",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "word_count",
        "description": "Counts the number of words in the given text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to count words in",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "character_count",
        "description": "Counts the number of characters (including spaces) in the given text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to count characters in",
                }
            },
            "required": ["text"],
        },
    },
    {
        "name": "shuffle_text",
        "description": "Randomly shuffles the characters in the given text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to shuffle",
                }
            },
            "required": ["text"],
        },
    },
]

def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution."""
    text = arguments.get("text", "")
    
    if name == "reverse_text":
        result = text[::-1]
        return {"content": [{"type": "text", "text": f"Reversed text: {result}"}]}
    
    elif name == "uppercase_text":
        result = text.upper()
        return {"content": [{"type": "text", "text": f"Uppercase: {result}"}]}
    
    elif name == "lowercase_text":
        result = text.lower()
        return {"content": [{"type": "text", "text": f"Lowercase: {result}"}]}
    
    elif name == "word_count":
        words = [w for w in text.split() if w]
        count = len(words)
        plural = "s" if count != 1 else ""
        return {"content": [{"type": "text", "text": f"Word count: {count} word{plural}"}]}
    
    elif name == "character_count":
        count = len(text)
        plural = "s" if count != 1 else ""
        return {"content": [{"type": "text", "text": f"Character count: {count} character{plural}"}]}
    
    elif name == "shuffle_text":
        chars = list(text)
        random.shuffle(chars)
        result = "".join(chars)
        return {"content": [{"type": "text", "text": f"Shuffled text: {result}"}]}
    
    else:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}

def handle_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle incoming MCP messages and return response."""
    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params", {})
    
    print(f"Handling message: method={method}, id={msg_id}")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "text-utilities-mcp-python",
                    "version": "1.0.0"
                }
            }
        }
    
    elif method == "notifications/initialized":
        # This is a notification, no response needed
        return None
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        result = handle_tool_call(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }
    
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {}
        }
    
    else:
        print(f"Unknown method: {method}")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "name": "text-utilities-mcp-python",
        "version": "1.0.0",
        "tools": [tool["name"] for tool in TOOLS],
        "activeSessions": len(active_sessions)
    }

# SSE endpoint
@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP communication."""
    print("New SSE connection established")
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    print(f"Session created: {session_id}")
    
    # Create message queue for this session
    message_queue: asyncio.Queue = asyncio.Queue()
    active_sessions[session_id] = message_queue
    
    # Get message endpoint from env or use default
    message_endpoint = os.getenv("MESSAGE_ENDPOINT", "/message")
    
    # If MESSAGE_ENDPOINT is a full URL, extract just the path
    try:
        parsed = urlparse(message_endpoint)
        if parsed.scheme:  # It's a full URL
            message_endpoint = parsed.path
        print(f"Using message endpoint: {message_endpoint}")
    except Exception as e:
        print(f"Using message endpoint as-is: {message_endpoint}")
    
    async def event_generator():
        try:
            # Send the endpoint event with session ID
            endpoint_url = f"{message_endpoint}?sessionId={session_id}"
            yield {
                "event": "endpoint",
                "data": endpoint_url
            }
            print(f"Sent endpoint event: {endpoint_url}")
            
            # Keep connection alive and send messages from queue
            while True:
                try:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        print(f"Client disconnected: {session_id}")
                        break
                    
                    # Wait for message with timeout (for keepalive)
                    try:
                        message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                        yield {
                            "event": "message",
                            "data": json.dumps(message)
                        }
                        print(f"Sent message to client: {json.dumps(message)[:100]}...")
                    except asyncio.TimeoutError:
                        # Send keepalive comment
                        yield {"comment": "keepalive"}
                        
                except Exception as e:
                    print(f"Error in event generator: {e}")
                    break
        finally:
            # Cleanup
            if session_id in active_sessions:
                del active_sessions[session_id]
                print(f"Session closed: {session_id}")
    
    return EventSourceResponse(event_generator())

# Message endpoint
@app.post("/message")
async def message_endpoint(
    request: Request,
    sessionId: str = Query(..., alias="sessionId")
):
    """Message endpoint for handling MCP messages."""
    print(f"[MESSAGE] Received POST request with sessionId: {sessionId}")
    print(f"[MESSAGE] Active sessions: {list(active_sessions.keys())}")
    
    message_queue = active_sessions.get(sessionId)
    
    if not message_queue:
        print(f"[MESSAGE] Session not found: {sessionId}")
        return JSONResponse(
            status_code=400,
            content={"error": "No active session found"}
        )
    
    try:
        body = await request.json()
        print(f"[MESSAGE] Received: {json.dumps(body)[:200]}...")
        
        # Handle the message
        response = handle_message(body)
        
        if response:
            # Queue the response to be sent via SSE
            await message_queue.put(response)
            print(f"[MESSAGE] Queued response: {json.dumps(response)[:100]}...")
        
        # Return accepted (the actual response goes via SSE)
        return Response(status_code=202, content="Accepted")
        
    except Exception as error:
        print(f"Error handling message: {error}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(error)}
        )

# Start the server
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    print(f"Text Utilities MCP Python running on port {port}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"SSE endpoint: http://localhost:{port}/sse")
    print(f"Available tools: {', '.join([tool['name'] for tool in TOOLS])}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
