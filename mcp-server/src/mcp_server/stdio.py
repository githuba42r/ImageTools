"""stdio transport entry point.

Usage:
  IMAGETOOLS_URL=http://localhost:8082 IMAGETOOLS_TOKEN=imt_... \\
    python -m mcp_server.stdio

NB: no `from __future__ import annotations` — mcp 1.12.x's tool
introspection TypeErrors on string parameter annotations.
"""

import asyncio
import os
import sys
from typing import Optional

import httpx

from .backend_http import HttpBackendClient
from . import tools as tool_fns
from mcp.server.fastmcp import FastMCP


async def _resolve_user_id(base_url: str, token: str) -> str:
    """Identify the user by calling the MCP whoami endpoint with the bearer
    token. Returns the user_id string, or raises on HTTP error."""
    async with httpx.AsyncClient(
        timeout=10.0, headers={"Authorization": f"Bearer {token}"}
    ) as client:
        r = await client.get(f"{base_url.rstrip('/')}/api/v1/mcp-tokens/whoami")
        r.raise_for_status()
        return r.json()["user_id"]


def _build_stdio_server(user_id: str, backend: HttpBackendClient) -> FastMCP:
    """FastMCP with auth disabled and user_id baked in from env-resolved token."""
    mcp = FastMCP("imagetools-stdio", json_response=True)

    @mcp.tool()
    async def list_recent_images(count: int = 10, tag: Optional[str] = None) -> dict:
        """List metadata for the N most recent images (newest first); optionally filter by tag."""
        return await tool_fns.list_recent_images(backend, user_id, count, tag=tag)

    @mcp.tool()
    async def get_image(id: str) -> list:
        """Fetch one image as an MCP image content block + metadata."""
        from .server import _to_mcp_content
        result = await tool_fns.get_image(backend, user_id, id)
        return _to_mcp_content(result["data"], result["mime_type"], result["meta"])

    @mcp.tool()
    async def get_recent_images(count: int = 1, tag: Optional[str] = None) -> list:
        """Fetch the N most recent images (up to 6) as MCP content blocks; optionally filter by tag."""
        from .server import _to_mcp_content
        result = await tool_fns.get_recent_images(backend, user_id, count, tag=tag)
        out: list = []
        for img in result["images"]:
            out.extend(_to_mcp_content(img["data"], img["mime_type"], img["meta"]))
        return out

    return mcp


def main() -> None:
    base_url = os.environ.get("IMAGETOOLS_URL")
    token = os.environ.get("IMAGETOOLS_TOKEN")
    if not base_url or not token:
        sys.stderr.write(
            "IMAGETOOLS_URL and IMAGETOOLS_TOKEN must be set.\n"
        )
        sys.exit(2)

    async def _run():
        user_id = await _resolve_user_id(base_url, token)
        backend = HttpBackendClient(base_url=base_url, token=token)
        mcp = _build_stdio_server(user_id, backend)
        try:
            # FastMCP.run is sync and starts its own event loop; we're already
            # inside one, so use run_stdio_async() instead.
            await mcp.run_stdio_async()
        finally:
            await backend.aclose()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
