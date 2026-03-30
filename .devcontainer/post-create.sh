#!/usr/bin/env bash
# Runs once after the devcontainer is created.
set -euo pipefail

echo "==> post-create: setting up workspace"

# Install Claude Code globally (Node is available here via the devcontainer feature)
echo "==> Installing Claude Code..."
npm install -g @anthropic-ai/claude-code

# Configure MCP servers for Claude Code
echo "==> Writing ~/.mcp.json..."
cat > ~/.mcp.json << 'EOF'
{
  "mcpServers": {
    "playwright": {
      "type": "sse",
      "url": "http://host.docker.internal:3001/sse"
    }
  }
}
EOF
