# Agent Sandbox Devcontainer

Runs Claude Code (or any agent) inside a Docker devcontainer for sandboxed execution while keeping the host Playwright MCP server accessible.

## Stack

- **Base image**: `mcr.microsoft.com/devcontainers/python:3.12-bookworm`
- **Node.js 22** — added via devcontainer feature
- **Python packages**: `requests`, `httpx`, `python-dotenv`, `rich`
- **Claude Code**: installed globally in `post-create.sh`
- **Playwright MCP**: runs on the host Mac, connected from container via SSE

## Prerequisites

- Docker Desktop running
- VS Code with the **Dev Containers** extension
- Node.js on the host (for running the Playwright MCP server)

## Setup

### 1. Start the Playwright MCP server on your Mac host

Open a terminal on your Mac and run:

```bash
npx @playwright/mcp --port 3001 --host 0.0.0.0 --allowed-hosts '*'
```

Leave this running. The devcontainer connects to it via `host.docker.internal:3001`.

### 2. Open the project in VS Code

```bash
code /path/to/devcontainer-mcp
```

Then reopen in container:

```
Cmd+Shift+P → Dev Containers: Reopen in Container
```

VS Code will build the image (first time ~2-3 min), then run `post-create.sh` which:
- Installs `@anthropic-ai/claude-code` globally
- Writes `/workspace/.mcp.json` pointing at the host Playwright MCP via SSE

### 3. Verify Claude Code sees the Playwright MCP

Inside the container terminal:

```bash
claude mcp list
# Should show: playwright  sse  http://host.docker.internal:3001/sse
```

### 4. Test Playwright MCP from inside the container

```bash
claude
```

Then prompt Claude Code:

> "Navigate to https://example.com and take a screenshot"

Claude Code will invoke the Playwright MCP running on your host — the browser opens on your Mac, and the result is returned to the container.

## MCP Configuration

The file `.mcp.example.json` is written by `post-create.sh` on first container creation: create the `.mcp.json` for devcontainer

```json
{
  "mcpServers": {
    "playwright": {
      "type": "sse",
      "url": "http://host.docker.internal:3001/sse"
    }
  }
}
```

This is the correct config location Claude Code reads from. The Playwright MCP server must be running on the host before Claude Code tries to use it.

## Architecture

```
┌──────────────────────────────────────────────┐
│  macOS Host                                  │
│                                              │
│  npx @playwright/mcp --port 3001             │
│    └── controls browser on host              │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Docker Devcontainer                   │  │
│  │                                        │  │
│  │  claude-code                           │  │
│  │    └── reads /workspace/.mcp.json      │  │
│  │    └── MCP client (SSE)                │  │
│  │         └── host.docker.internal:3001  │  │
│  │                                        │  │
│  │  /workspace  ←→  host project folder   │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

## Volume Mount

The project folder is mounted at `/workspace` inside the container — edits in either place are immediately reflected in the other.

## Forwarded Ports

| Port | Service |
|------|---------|
| 5173 | Vite dev server |
