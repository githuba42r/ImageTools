"""Regression test for the MCP-vs-SPA route shadowing bug.

The MCP server is mounted at "/mcp". The frontend SPA registers a
"/{full_path:path}" catch-all that returns index.html for unmatched routes.
Starlette matches routes in registration order, so the "/mcp" Mount MUST be
registered before the catch-all. When it was mounted inside the lifespan
(which runs after import, i.e. after the catch-all was registered) every
/mcp request was served the SPA HTML with 200, which made streamable-HTTP
MCP clients (Claude Code / Claude.ai) fail the event stream and reconnect
in a tight loop.

This test pins the invariant at the route-table level so a regression
(moving the mount back into the lifespan, or dropping the catch-all guard)
fails fast without needing a running server.
"""
import inspect

from starlette.routing import Mount


def _load_app():
    # Imported lazily inside the test so the rest of the suite (which uses a
    # minimal app via conftest and never imports app.main) is unaffected.
    from app.core.rate_limit import reset_for_tests
    from app.main import app

    # app.main import initialises the shared rate limiter; reset it so this
    # test does not pollute rate-limit tests.
    reset_for_tests()
    return app


def test_mcp_mount_registered_before_spa_catch_all():
    app = _load_app()

    mcp_idx = None
    catch_idx = None
    for i, route in enumerate(app.router.routes):
        path = getattr(route, "path", getattr(route, "path_format", ""))
        if isinstance(route, Mount) and path == "/mcp":
            mcp_idx = i
        if path == "/{full_path:path}":
            catch_idx = i

    assert mcp_idx is not None, (
        "/mcp Mount is not registered on app.router.routes — it must be "
        "mounted at import time, not inside the lifespan."
    )
    if catch_idx is not None:
        assert mcp_idx < catch_idx, (
            f"/mcp Mount (index {mcp_idx}) must precede the SPA catch-all "
            f"(index {catch_idx}); otherwise /mcp is shadowed by index.html."
        )


def test_spa_catch_all_excludes_mcp_as_defense_in_depth():
    """The catch-all must fall through (404) for mcp paths even if it is
    ever reached, instead of returning the SPA HTML."""
    app = _load_app()

    serve_frontend = None
    for route in app.router.routes:
        if getattr(route, "path", "") == "/{full_path:path}":
            serve_frontend = route.endpoint
            break

    if serve_frontend is None:
        # Frontend build absent in this environment: the catch-all is not
        # registered, so the route-order test fully covers the bug. The
        # exclusion guard is verified by source inspection instead.
        from app import main

        src = inspect.getsource(main)
        assert 'full_path == "mcp"' in src and 'full_path.startswith("mcp/")' in src
        return

    import asyncio

    for p in ("mcp", "mcp/", "mcp/anything"):
        result = asyncio.get_event_loop().run_until_complete(serve_frontend(p))
        assert result == {"detail": "Not Found"}, (
            f"catch-all must 404 for {p!r}, got {result!r}"
        )
