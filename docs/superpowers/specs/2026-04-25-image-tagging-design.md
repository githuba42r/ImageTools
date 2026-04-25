# Image Tagging — Design

**Date:** 2026-04-25
**Branch:** `feature/mcp-server`
**Status:** Approved
**Supersedes "future scope" section in:** `docs/superpowers/specs/2026-04-23-mcp-server-design.md`

## Goal

Let users attach a freetext tag to screenshots at upload time so the
ImageTools MCP server can retrieve images by tag, e.g. *"look at the last 2
ImageTools images tagged POS-table-service"*. A "current tag" set in the
browser addon and Android app is applied to every subsequent upload until
the user changes or clears it. An autocomplete typeahead lets users converge
on consistent tag names by reusing tags they have used before.

Tags exist primarily to make MCP retrieval ergonomic. They are not a general
organisation feature for the web UI; the web UI displays tag chips but does
not need an edit/filter surface in this iteration.

## Scope

### In scope

- New `tags` JSON-array column on `images`, persisted via an explicit
  migration (existing rows backfilled with `[]`).
- Optional `tag` form field on the addon, mobile, and frontend upload
  endpoints.
- New `GET /api/v1/users/{user_id}/tags` endpoint returning the user's
  distinct tags for autocomplete.
- New `PUT /api/v1/images/{id}/tags` endpoint for future tag editing.
- Browser addons (Chrome + Firefox): "current tag" input in the popup with
  datalist autocomplete from the `tags` endpoint, persisted across popup
  opens via `browser.storage.local`, applied to every upload until cleared.
- Android: tag input on the upload screen with `AutoCompleteTextView`
  populated from `tags` endpoint, persisted across uploads via
  SharedPreferences.
- MCP: extend `list_recent_images` and `get_recent_images` with an optional
  `tag` arg; include `tags` field in metadata returned by all three tools.
- Web frontend: render tag chips on image cards (read-only).

### Out of scope (deferred)

- Multi-tag UI on the addon (single "current tag" is sufficient for the
  upload flow; the data model already supports many).
- Tag editing UI on the web frontend (the `PUT /tags` endpoint is shipped to
  unblock this in a follow-up).
- Tag rename across all images, tag categories / hierarchy, automatic tag
  suggestions from image content.
- Tag-based filtering or search in the web gallery.

## Architecture

### Data model

`images.tags` — `Column(Text, nullable=False, server_default="[]")`. JSON
array, accessed via small helpers on `ImageService` (`set_tags`, `get_tags`).
Storing as an array even though uploads attach one tag at a time, because
(a) future multi-tag UI lands without another migration, (b) MCP filtering
can match any element, and (c) the cost is identical to a single-string
column.

### Backend

- **Migration.** `app/core/migrate.py` gains a block that adds the column to
  existing databases when missing. SQLite supports `ALTER TABLE ADD COLUMN`
  with a default; we explicitly populate `[]` for any existing rows.
- **Upload endpoints.** Three endpoints accept an optional `tag` field:
  - `POST /api/v1/images` (frontend uploads)
  - `POST /api/v1/addon/upload` (browser addons)
  - `POST /api/v1/mobile/upload` (Android)
  Tag normalisation: trim, reject empty after trim, cap length at 64
  characters. Stored as a single-element array `[tag]`.
- **Tag listing.**
  `GET /api/v1/users/{user_id}/tags` → `[{"tag": str, "last_used_at": iso}]`,
  ordered by `MAX(created_at) DESC`. Backed by a SQL aggregate over
  `images.tags` using SQLite's `json_each`.
- **Tag editing (forward compat).**
  `PUT /api/v1/images/{id}/tags` with body `{"tags": ["a", "b"]}` — replaces
  the array. Server normalises and dedupes.
- **`ImageResponse` schema** gains `tags: list[str]`.

### Browser addons (Chrome + Firefox)

The two addons share most of their code. Changes are mirrored:

- `popup.html`: a `<input list="…">` with a `<datalist>` populated from the
  tags endpoint, plus an inline clear-X button.
- `popup.js`: on popup open, read the current tag from `browser.storage.local`
  and prefill the input; refetch the user's tag list and write it to the
  datalist; on input change, persist back to storage; on clear, remove the
  storage key.
- `content.js` and `background.js`: when uploading, read the current tag
  from storage and include it as a `tag` form field on the multipart POST.

### Android

- Upload screen (`UploadActivity` / equivalent): an `AutoCompleteTextView`
  for the tag, populated from the tags endpoint via the existing
  `ApiService` once per screen-open.
- Persistence in `SharedPreferences` under a single string key.
- Multipart upload includes the tag as a form field.

### MCP server

Extends the existing tool handlers, no new tool surface:

- `list_recent_images(count: int = 10, tag: str | None = None)`
- `get_recent_images(count: int = 1, tag: str | None = None)`
- `get_image(id: str)` — unchanged.

Tag filtering is implemented in the `BackendClient` Protocol so both the
in-process (HTTP transport) and REST-backed (stdio transport) clients honour
it. Local client adds a `WHERE` clause using `json_each(tags)` plus a
case-insensitive comparison. HTTP client passes the tag as a query parameter
to `/api/v1/images/user/{user_id}?tag=…`.

The `ImageMeta` dataclass returned by the backend gains a `tags: list[str]`
field; tool responses now include `tags` in each image's metadata block so
the LLM can see what each image is tagged with even when it didn't filter.

### Web frontend

`ImageCard.vue` renders a small horizontal row of tag chips beneath the
filename if `image.tags` is non-empty. No interactivity in this iteration.

## Tag matching semantics

- Equality is **case-insensitive exact match** after trimming both the
  filter tag and the stored tags. e.g. `pos-table-service`,
  `POS-Table-Service`, and `POS-table-service` all collide.
- Tags are stored exactly as the user entered them (case preserved); only
  comparison is case-insensitive. Autocomplete returns the most-recent
  casing.
- No partial matching, no fuzzy search, no prefix expansion. The MCP prompt
  is precise; the user knows their tags.

## Data flow

1. User opens the browser addon, types `POS-table-service` in the Current
   Tag input. Stored in `browser.storage.local`.
2. User captures a selection screenshot. The addon POSTs the multipart
   upload with `tag=POS-table-service`.
3. Backend stores the image with `tags=["POS-table-service"]`.
4. User asks Claude Code: *"look at the last 2 ImageTools images tagged
   POS-table-service"*.
5. Claude calls `get_recent_images(count=2, tag="POS-table-service")` over
   MCP.
6. Backend filters by tag, returns the two newest matching images as
   content blocks; metadata text blocks include the tag.

## Error handling

| Condition | Behaviour |
|---|---|
| Tag exceeds 64 chars | 400 from upload endpoints; addon shows inline validation |
| Empty tag after trim | Treated as untagged (no tag stored, normal upload) |
| Tag list endpoint fails (network) | Addon/Android falls back to empty datalist; user can still type freely |
| MCP `tag` filter matches no images | Empty `images: []` plus `clamped: false` — same shape as the no-images case today |
| Migration fails on existing DB | Backend startup fails loudly; matches the existing migration error path |

## Testing

- Unit: `ImageService` get/set tags helpers; tag normalisation; tag list
  aggregation; MCP tool handlers with tag filter (extends the existing
  `FakeBackend` to honour `tag`).
- Integration: upload through the existing endpoints with and without `tag`,
  retrieve via tags endpoint, retrieve via MCP filter.
- Manual: addon popup persistence across closes; android persistence across
  app restarts.

## File touch list

**Backend**
- `backend/app/models/models.py` — add `tags` column to `Image`
- `backend/app/core/migrate.py` — add column to existing rows
- `backend/app/services/image_service.py` — `set_tags`, `get_tags`,
  `list_user_tags`, accept tag in upload helpers
- `backend/app/schemas/image.py` — `tags` on `ImageResponse`
- `backend/app/api/v1/endpoints/images.py` — accept `tag` form field, add
  `PUT /tags`
- `backend/app/api/v1/endpoints/addon.py` — accept `tag` form field
- `backend/app/api/v1/endpoints/mobile.py` — accept `tag` form field
- `backend/app/api/v1/endpoints/users.py` (or new `tags.py`) — `GET tags`

**MCP**
- `mcp-server/src/mcp_server/backend.py` — `tags` on `ImageMeta`
- `mcp-server/src/mcp_server/backend_local.py` — tag filter via
  `json_each`
- `mcp-server/src/mcp_server/backend_http.py` — pass `tag` as query param
- `mcp-server/src/mcp_server/tools.py` — `tag` arg on list/get_recent
- `mcp-server/src/mcp_server/server.py` — propagate to FastMCP tool sigs
- `mcp-server/src/mcp_server/stdio.py` — propagate to stdio tool sigs

**Browser addons** (Chrome + Firefox, mirror)
- `browser-addons/{chrome,firefox}/popup.html`
- `browser-addons/{chrome,firefox}/popup.js`
- `browser-addons/{chrome,firefox}/content.js`
- `browser-addons/{chrome,firefox}/background.js`

**Android**
- `android-app/app/src/main/.../UploadActivity.kt` (or equivalent)
- `android-app/app/src/main/res/layout/activity_upload.xml`
- `android-app/app/src/main/.../ApiService.kt`

**Frontend**
- `frontend/src/components/ImageCard.vue` — render tag chips

## Tests

- `backend/tests/test_image_service_tags.py`
- `backend/tests/test_mcp_tools.py` — extend existing tests with tag-filter
  cases against the existing `FakeBackend`

(No tests added for browser addons or Android; no test infra exists for
those today, and adding it is out of scope for this feature.)
