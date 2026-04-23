"""Helpers for mounting the MCP Streamable HTTP app inside the FastAPI backend."""
from __future__ import annotations

import contextlib
from typing import Callable

from mcp.server.fastmcp import FastMCP


@contextlib.asynccontextmanager
async def mcp_lifespan(mcp: FastMCP):
    """ASGI lifespan helper to run the MCP session manager."""
    async with mcp.session_manager.run():
        yield


def build_backend_mcp(session_factory, verify_token) -> FastMCP:
    """Build a FastMCP server wired to in-process DB access."""
    from .backend_local import LocalBackendClient
    from .server import build_server
    backend = LocalBackendClient(session_factory=session_factory)
    return build_server(backend, verify_token)
