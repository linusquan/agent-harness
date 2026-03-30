# Lean Python base — Node added via devcontainer feature
FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# Install Claude Code globally (Node is added by the devcontainer feature)
# This runs in postCreateCommand instead since Node isn't available at build time.

# Python: install common data/scripting packages
RUN pip3 install --no-cache-dir \
    requests \
    httpx \
    python-dotenv \
    rich

# Playwright MCP runs on the HOST — no browser installation needed in the container.
# The container connects to the host server via SSE (host.docker.internal:3001).
