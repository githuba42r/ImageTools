# ImageTools MCP Server

Exposes your recent ImageTools screenshots to Claude Code (and other MCP clients)
so you can ask the LLM to reason about them: *"use my last 2 screenshots; the
first shows the bug, the second shows the expected layout"*.

Two transports; pick whichever fits your setup.

## Streamable HTTP (for a deployed backend)

The MCP endpoint is served by the existing ImageTools backend at `/mcp/` —
nothing extra to install, no extra port to open.

1. In the ImageTools web UI, open Settings → **MCP Access Tokens** → New Token.
   Give it a label like `laptop claude-code`. Copy the `imt_…` token — it
   is shown only once.
2. Add this entry to your Claude Code MCP config
   (`~/.claude/mcp.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "imagetools": {
      "url": "https://imagetools.example.com/mcp/",
      "headers": { "Authorization": "Bearer imt_YOUR_TOKEN_HERE" }
    }
  }
}
```

3. Restart Claude Code. Verify by asking it: *"list my 3 most recent
   ImageTools screenshots"*.

## stdio (for local dev / tunnelling)

The stdio transport runs a small Python process on your machine that calls the
ImageTools REST API.

1. Install the package (requires Python 3.11+):

```bash
pip install -e /path/to/ImageTools/mcp-server
```

2. Mint a token as above. Then configure Claude Code:

```json
{
  "mcpServers": {
    "imagetools": {
      "command": "python",
      "args": ["-m", "mcp_server.stdio"],
      "env": {
        "IMAGETOOLS_URL": "http://localhost:8082",
        "IMAGETOOLS_TOKEN": "imt_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

## Tools exposed

| Tool | Args | Returns |
|---|---|---|
| `list_recent_images` | `count: int = 10` (max 50) | Metadata list, newest first |
| `get_image` | `id: str` | Image bytes + metadata |
| `get_recent_images` | `count: int = 1` (max 6) | Up to N images + metadata, newest first |

## Revoking access

From the web UI's MCP Access Tokens screen, click **Revoke** on any row.
Revocation is immediate; subsequent MCP calls with that token will fail with
401.
