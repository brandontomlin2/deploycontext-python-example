# Python MCP Server Example

A Python implementation of a Model Context Protocol (MCP) server with text utility tools.

## Features

This MCP server provides the following text manipulation tools:

- **reverse_text** - Reverses the order of characters in text
- **uppercase_text** - Converts text to uppercase
- **lowercase_text** - Converts text to lowercase
- **word_count** - Counts the number of words in text
- **character_count** - Counts the number of characters in text
- **shuffle_text** - Randomly shuffles characters in text

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
python server.py
```

The server will start on port 8081 (or the PORT environment variable if set).

## Endpoints

- `GET /health` - Health check endpoint
- `GET /sse` - SSE endpoint for MCP communication
- `POST /message?sessionId=<id>` - Message endpoint for handling MCP requests

## Environment Variables

- `PORT` - Port to run the server on (default: 8081)
- `MESSAGE_ENDPOINT` - Endpoint path for messages (default: /message)

## Deployment

This server is designed to be deployed via MCPHub. It will automatically:

1. Detect Python runtime from `requirements.txt`
2. Validate MCP SDK dependency (`mcp` package)
3. Generate appropriate Dockerfile
4. Deploy to Fly.io

## Testing

After deployment, you can test the server by:

1. Checking the health endpoint: `GET https://your-app.fly.dev/health`
2. Connecting via MCP client using the SSE endpoint
