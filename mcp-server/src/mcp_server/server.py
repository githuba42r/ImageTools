"""FastMCP server wiring: tools + token verification."""
from __future__ import annotations

import base64
from typing import Any, Callable

from mcp.server.fastmcp import Context, FastMCP, Image
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.middleware.auth_context import get_access_token

from .backend import BackendClient
from . import tools as tool_fns


class McpTokenVerifier(TokenVerifier):
    """Validates an ImageTools personal access token against the DB.

    The callable must be async: `async def verify(token) -> str | None` where
    the return value is the user_id (or None for invalid tokens). This keeps
    the verifier decoupled from SQLAlchemy so the stdio transport can use a
    REST-based verifier if needed.
    """

    def __init__(self, verify: Callable):
        self._verify = verify

    async def verify_token(self, token: str) -> AccessToken | None:
        user_id = await self._verify(token)
        if user_id is None:
            return None
        return AccessToken(
            token=token,
            client_id=user_id,   # we repurpose client_id as user_id
            scopes=["mcp:images:read"],
            expires_at=None,
        )


def build_server(backend: BackendClient, verify_token, *, name: str = "imagetools") -> FastMCP:
    """Build a FastMCP instance wired up with our tools and (optional) auth.

    `verify_token`: async (str) -> str | None returning user_id. Pass None to
    disable auth (stdio local use only).
    """
    if verify_token is not None:
        from mcp.server.auth.settings import AuthSettings
        from pydantic import AnyHttpUrl
        mcp = FastMCP(
            name,
            json_response=True,
            token_verifier=McpTokenVerifier(verify_token),
            auth=AuthSettings(
                issuer_url=AnyHttpUrl("https://imagetools.local/"),
                resource_server_url=AnyHttpUrl("https://imagetools.local/"),
                required_scopes=["mcp:images:read"],
            ),
        )
    else:
        mcp = FastMCP(name, json_response=True)

    def _user_id(ctx: Context) -> str:  # noqa: ARG001 — ctx kept for type annotation
        tok = get_access_token()
        if tok is None or not tok.client_id:
            raise RuntimeError("no authenticated user in context")
        return tok.client_id

    @mcp.tool()
    async def list_recent_images(count: int = 10, ctx: Context = None) -> dict[str, Any]:
        """List metadata for the N most recent images for the authenticated user,
        newest first. Does not return image bytes — use get_image or
        get_recent_images to fetch content."""
        return await tool_fns.list_recent_images(backend, _user_id(ctx), count)

    @mcp.tool()
    async def get_image(id: str, ctx: Context = None) -> list:
        """Fetch one image by id as an MCP image content block, along with
        its metadata."""
        result = await tool_fns.get_image(backend, _user_id(ctx), id)
        return _to_mcp_content(result["data"], result["mime_type"], result["meta"])

    @mcp.tool()
    async def get_recent_images(count: int = 1, ctx: Context = None) -> list:
        """Fetch the N most recent images (up to 6) as MCP image content blocks,
        newest first, with metadata for each. For larger batches use
        list_recent_images + get_image."""
        result = await tool_fns.get_recent_images(backend, _user_id(ctx), count)
        out: list = []
        for img in result["images"]:
            out.extend(_to_mcp_content(img["data"], img["mime_type"], img["meta"]))
        return out

    return mcp


def _to_mcp_content(data: bytes, mime_type: str, meta: dict) -> list:
    """Package raw image bytes + metadata into MCP content blocks."""
    try:
        # Image() handles base64 encoding; we pass through format as lowercase.
        fmt = mime_type.split("/", 1)[1]
        img = Image(data=data, format=fmt)
    except Exception:
        # Fall back to constructing ImageContent directly with base64
        from mcp.types import ImageContent
        img = ImageContent(
            type="image",
            data=base64.b64encode(data).decode(),
            mimeType=mime_type,
        )
    # Return both the image block and a text block describing the metadata so
    # the LLM can correlate "first image" with its filename/timestamp/size.
    return [
        img,
        (
            f"Image id={meta['id']} filename={meta['original_filename']} "
            f"created_at={meta['created_at']} size={meta['current_size']} "
            f"{meta['width']}x{meta['height']} format={meta['format']}"
        ),
    ]
