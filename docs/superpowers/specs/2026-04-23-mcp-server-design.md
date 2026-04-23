# MCP Server for ImageTools — Design

**Date:** 2026-04-23
**Branch:** `feature/mcp-server`
**Status:** Proposed

## Goal

Expose a Model Context Protocol (MCP) server that lets Claude Code (and other MCP
clients) retrieve recent screenshots from a user's ImageTools account. The user
drives the workflow from the Claude Code prompt — e.g. *"use my last 2 screenshots:
the first shows the checkout-button bug, the second shows the expected layout"* — and
the MCP server's job is to hand over images and just enough metadata for the LLM
to correlate them with the prompt.

## Scope

### In scope (this iteration)

- Retrieve recent images by recency for an authenticated user.
- Read-only: list + fetch. No delete/edit from MCP.
- Two transports from one codebase:
  - **Streamable HTTP** (primary) — for the remote, Dockerised deployment.
  - **stdio** (secondary) — for local development.
- Personal access token auth, minted from the existing web UI, used by both transports.

### Out of scope (explicit future work)

- **Tag-based retrieval.** Sketch: add a `tags` column to `images`, extend the browser
  addon with a "current tag" setting that is applied to uploads until the user changes
  it, and add an MCP tool `get_images_by_tag(tag, count)`. Enables prompts like
  *"retrieve the last 2 pos-tagged images"*, which scales better than recency when the
  user juggles multiple concurrent features. Tracked for the next iteration.
- Write operations from MCP (delete, edit, compress).
- Non-recency search (filename search, date range, similarity).

## Architecture

One Python package, `mcp_server/`, with two entry points sharing the same tool
handlers:

1. **HTTP transport (primary).** A FastAPI sub-router mounted at `/mcp/` inside
   the existing backend. Same container, same reverse proxy, same auth posture
   as the rest of the API. Implements the MCP Streamable HTTP transport. This is
   the path a remote Claude Code client uses.

2. **stdio transport (secondary).** `python -m mcp_server.stdio` entry point.
   Speaks MCP over stdin/stdout to a local Claude Code process and talks to the
   ImageTools backend over HTTP internally (using the same access token). Useful
   for local dev, debugging, or when tunnelling from a developer laptop.

Both entry points share the same tool handlers
(`list_recent_images`, `get_image`, `get_recent_images`). Only transport wiring
and how the access token is surfaced differ.

```
┌───────────────────────────┐         ┌──────────────────────────────────┐
│ Claude Code               │  HTTP   │ ImageTools backend (Docker)       │
│   ↓ MCP client            │────────▶│   /mcp/  ← FastAPI sub-router     │
│                           │ Bearer  │     ↓                             │
└───────────────────────────┘ token   │   mcp_server tool handlers        │
                                      │     ↓                             │
┌───────────────────────────┐ stdio   │   ImageService + file storage     │
│ Claude Code (local)       │ pipe    │                                   │
│   ↓ python -m             │────────▶│  (stdio entry calls the backend   │
│     mcp_server.stdio      │         │   over HTTP with the same token)  │
└───────────────────────────┘         └──────────────────────────────────┘
```

## Authentication

A single "MCP access token" concept, generated from the ImageTools web UI in a
new section next to the existing Addon management screen.

Properties:

- Identifies exactly one user.
- Long-lived (no refresh-token dance). The user revokes from the web UI if
  compromised.
- Presented as `Authorization: Bearer <token>` by the HTTP transport and as
  the `IMAGETOOLS_TOKEN` env var by the stdio transport. The stdio entry point
  also reads `IMAGETOOLS_URL` (e.g. `https://imagetools.example.com`) so it
  knows which backend to call; it forwards the same token as a bearer header
  on those calls. Token validation is therefore one path regardless of
  transport.

New table `mcp_authorizations` (kept separate from `addon_authorizations`
because the lifecycles differ — addon tokens are short-lived with refresh
tokens, MCP tokens are long-lived personal access tokens):

| Column          | Type          | Notes                                     |
|-----------------|---------------|-------------------------------------------|
| `id`            | String PK     | UUID                                      |
| `user_id`       | FK → users    | Indexed, cascade delete                   |
| `token_hash`    | String        | sha256 of plaintext; unique index         |
| `label`         | String        | User-provided, e.g. "laptop claude-code"  |
| `created_at`    | DateTime      | Server default                            |
| `last_used_at`  | DateTime      | Nullable; updated on each validated call  |
| `revoked_at`    | DateTime      | Nullable; presence = revoked              |

The plaintext token is shown exactly once, at creation, for the user to copy
into their Claude Code MCP config. Thereafter only the hash is stored.

## Tools

### `list_recent_images`

**Args:** `count: int = 10` (clamped server-side to `1..50`)

**Returns:** JSON list, newest first. Each entry:

```json
{
  "id": "b3c4-…",
  "original_filename": "screenshot-2026-04-23-1022.png",
  "created_at": "2026-04-23T10:22:11Z",
  "width": 1920,
  "height": 1080,
  "format": "PNG",
  "current_size": 482110
}
```

No image bytes. Lets Claude show the user a list and confirm before pulling
content.

### `get_image`

**Args:** `id: str`

**Returns:** One MCP image content block (base64-encoded PNG/JPEG per the
image's native format) plus a text block containing the metadata above.
Handles targeted fetches such as *"the fourth last image"* after a
`list_recent_images` call.

### `get_recent_images`

**Args:** `count: int = 1` (clamped server-side to `1..6`)

**Returns:** Up to `count` image content blocks plus per-image metadata text
blocks, newest first. Convenience for the dominant case — *"use my last 2
images"* — in one round trip.

The cap of 6 in this iteration is deliberate. For larger batches the user
chains `list_recent_images` + individual `get_image` calls, which keeps the
expensive path explicit.

## Data flow

1. User asks Claude Code: *"use my last 2 ImageTools screenshots; the first is
   the bug, the second is the expected layout."*
2. Claude Code calls the MCP server's `get_recent_images(count=2)` tool with
   the configured bearer token.
3. MCP server validates the token against `mcp_authorizations`, resolves
   `user_id`, and updates `last_used_at`.
4. Handler calls `ImageService.get_user_images(user_id, limit=2, order='created_at DESC')`.
5. For each image, reads the file at `image.current_path`, base64-encodes it,
   and wraps it in an MCP image content block with a sibling text block of
   metadata.
6. Response returns to Claude Code. The LLM now has the bytes of the two
   screenshots alongside the user's prompt describing what each shows.

For the HTTP transport, steps 4–5 are direct in-process calls. For stdio,
they are HTTP calls from the stdio entry point to the backend.

## Error handling

| Condition                              | Behaviour                                                     |
|----------------------------------------|---------------------------------------------------------------|
| Missing/invalid/revoked token          | MCP error, code `unauthorized`, plain message                 |
| `count` out of range                   | Clamped to the allowed range; included as a note in response  |
| Image row exists but file is missing   | Skipped, warning included in response (partial results ok)    |
| Backend unreachable (stdio case)       | MCP error, code `internal_error`                              |
| No images found for user               | Empty list (for `list_recent_images`); MCP error `not_found` for the bytes-returning tools |

## Testing

- Unit tests per tool handler with a mocked `ImageService` — token resolution,
  count clamping, metadata shape, missing-file handling.
- Integration test: backend with an in-memory SQLite, a seeded user, a minted
  MCP token, and both entry points (HTTP via `httpx.AsyncClient`, stdio via
  subprocess) calling each tool. Assert content blocks + metadata.
- Auth tests: revoked token, malformed token, missing token, wrong scheme —
  each producing the correct MCP error.
- No Claude Code end-to-end test this iteration. A manual smoke test against a
  real Claude Code client is the completion criterion.

## Deployment

- HTTP transport: no new container. Backend Dockerfile unchanged. New
  `/mcp/` routes loaded at startup alongside existing routers.
- stdio transport: documented in `mcp-server/README.md` with the exact
  `~/.claude/mcp.json` snippet to paste. Requires Python 3.11+ (matches
  backend requirement) and the `mcp` SDK.
- Web UI: one new "MCP Access Tokens" screen next to Addon management.
  Create → show plaintext once → list → revoke.

## File layout

```
mcp-server/                          # new, top-level
├── README.md                        # setup for both transports
├── pyproject.toml                   # mcp SDK + minimal deps
└── src/mcp_server/
    ├── __init__.py
    ├── tools.py                     # shared tool handlers
    ├── auth.py                      # token → user_id resolution
    ├── http_app.py                  # FastAPI sub-router (mounted by backend)
    └── stdio.py                     # stdio entry point
backend/app/api/v1/endpoints/
└── mcp_tokens.py                    # new: CRUD for MCP access tokens
backend/app/models/models.py         # + McpAuthorization model
frontend/src/components/
└── McpTokenManager.vue              # new: UI for minting/revoking tokens
```

The handlers and auth logic live under `mcp-server/` so they are self-contained
and future-portable (e.g. packaged separately). The backend imports the HTTP
sub-router and mounts it; the stdio entry is runnable standalone.

## Open decisions resolved in this spec

- **Auth table:** separate `mcp_authorizations`, not an extension of
  `addon_authorizations`, because token lifecycles diverge.
- **Token UX:** personal access token (show once, long-lived, user revokes).
  Not OAuth, not refresh-based.
- **Tool shape:** three tools — `list_recent_images`, `get_image`,
  `get_recent_images`. `list` + `get_image` is sufficient; `get_recent_images`
  stays because it saves a round trip for the dominant workflow.
- **Ordering:** `created_at DESC`. "Last image" = most recently uploaded.
- **Tagging:** explicitly deferred; documented in Future work.
