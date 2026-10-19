#!/usr/bin/env python3
"""Decide what the extension-release workflow should do for each browser add-on.

The workflow passes in which extensions changed and whether the last commit
touching each one is the workflow's own auto-bump commit. This script asks each
store what versions it already knows about, then prints a JSON plan:

    bump        - a new version is needed before submitting
    publish     - the manifest version is already ahead of the store
    skip        - nothing to do (no change, already submitted, or first review)
    unconfigured - store credentials are not set

Only the standard library is used so the workflow needs no extra Python deps.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHROME_MANIFEST = ROOT / "browser-addons" / "chrome" / "manifest.json"
FIREFOX_MANIFEST = ROOT / "browser-addons" / "firefox" / "manifest.json"

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
CHROME_STATUS_URL = (
    "https://chromewebstore.googleapis.com/v2/publishers/"
    "{publisher}/items/{item}:fetchStatus"
)
AMO_ADDON_ID = "imagetools@a42r.com"
AMO_VERSIONS_URL = (
    "https://addons.mozilla.org/api/v5/addons/addon/{addon}/versions/?page_size=100"
)

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def version_tuple(value: str | None) -> tuple[int, int, int] | None:
    if not value or not VERSION_RE.match(value):
        return None
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def next_patch(value: str) -> str:
    major, minor, patch = (int(part) for part in value.split("."))
    return f"{major}.{minor}.{patch + 1}"


def http_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    method: str | None = None,
) -> dict:
    request = urllib.request.Request(
        url, data=data, headers=dict(headers or {}), method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:800]
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc
    return json.loads(body) if body.strip() else {}


def read_manifest_version(path: Path) -> str:
    return json.loads(path.read_text())["version"]


def manifest_version_is_valid(value: str) -> bool:
    return VERSION_RE.match(value) is not None


# --------------------------------------------------------------------------
# Chrome Web Store
# --------------------------------------------------------------------------

CHROME_ENV = (
    "CHROME_CLIENT_ID",
    "CHROME_CLIENT_SECRET",
    "CHROME_REFRESH_TOKEN",
    "CHROME_EXTENSION_ID",
    "CHROME_PUBLISHER_ID",
)


def chrome_configured() -> bool:
    return all(os.environ.get(name) for name in CHROME_ENV)


def google_access_token() -> str:
    data = urllib.parse.urlencode(
        {
            "client_id": os.environ["CHROME_CLIENT_ID"],
            "client_secret": os.environ["CHROME_CLIENT_SECRET"],
            "refresh_token": os.environ["CHROME_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }
    ).encode()
    payload = http_json(
        GOOGLE_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
        method="POST",
    )
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"Google token exchange returned no access_token: {payload}")
    return token


def chrome_store_state() -> dict:
    token = google_access_token()
    url = CHROME_STATUS_URL.format(
        publisher=os.environ["CHROME_PUBLISHER_ID"],
        item=os.environ["CHROME_EXTENSION_ID"],
    )
    try:
        status = http_json(url, headers={"Authorization": f"Bearer {token}"})
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            raise RuntimeError(
                "Chrome Web Store item not found. Create the item in the developer "
                "dashboard first; the API can only update existing items."
            ) from exc
        raise

    if status.get("takenDown"):
        raise RuntimeError(
            "The Chrome Web Store item is taken down; resolve it in the dashboard first"
        )

    def crx_version(field: str) -> str | None:
        revision = status.get(field) or {}
        channels = revision.get("distributionChannels") or []
        return channels[0].get("crxVersion") if channels else None

    published = crx_version("publishedItemRevisionStatus")
    submitted = crx_version("submittedItemRevisionStatus")
    known = [value for value in (published, submitted) if version_tuple(value)]
    return {
        "published": published,
        "submitted": submitted,
        # Never published, but a revision has been submitted: first review.
        "first_review_pending": published is None and submitted is not None,
        "max": max(known, key=version_tuple) if known else None,
    }


# --------------------------------------------------------------------------
# Mozilla Add-ons (AMO)
# --------------------------------------------------------------------------

def amo_configured() -> bool:
    return bool(os.environ.get("WEB_EXT_API_KEY") and os.environ.get("WEB_EXT_API_SECRET"))


def _b64url(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def amo_jwt(api_key: str, api_secret: str) -> str:
    """Build the short-lived HS256 JWT AMO expects in `Authorization: JWT ...`."""
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"iss": api_key, "jti": uuid.uuid4().hex, "iat": now, "exp": now + 60}
    signing_input = b".".join(
        [
            _b64url(json.dumps(header, separators=(",", ":")).encode()),
            _b64url(json.dumps(payload, separators=(",", ":")).encode()),
        ]
    )
    signature = _b64url(
        hmac.new(api_secret.encode(), signing_input, hashlib.sha256).digest()
    )
    return b".".join([signing_input, signature]).decode()


def firefox_store_state() -> dict:
    token = amo_jwt(os.environ["WEB_EXT_API_KEY"], os.environ["WEB_EXT_API_SECRET"])
    url = AMO_VERSIONS_URL.format(addon=urllib.parse.quote(AMO_ADDON_ID, safe=""))
    payload = http_json(url, headers={"Authorization": f"JWT {token}"})
    rows = payload.get("results") or []
    versions = [
        row.get("version")
        for row in rows
        if version_tuple(row.get("version"))
    ]
    statuses = {
        row.get("version"): (row.get("file") or {}).get("status") for row in rows
    }
    return {
        "versions": versions,
        "statuses": statuses,
        "max": max(versions, key=version_tuple) if versions else None,
    }


# --------------------------------------------------------------------------
# Decision
# --------------------------------------------------------------------------

def decide(
    current: str,
    already_bumped: bool,
    store: dict | None,
    *,
    label: str,
    pending_first_review: bool = False,
) -> dict:
    if store is None:
        return {
            "action": "unconfigured",
            "target": None,
            "reason": f"{label} credentials are not configured",
        }

    if pending_first_review:
        return {
            "action": "skip",
            "target": None,
            "reason": (
                f"{label} submission {store.get('submitted')} is awaiting its first "
                "review; re-run after it is approved"
            ),
        }

    store_max = store.get("max")
    if store_max is None or version_tuple(current) > version_tuple(store_max):
        return {
            "action": "publish",
            "target": current,
            "reason": f"{label} has {store_max or 'no releases'}; manifest {current} is ahead",
        }

    if already_bumped:
        return {
            "action": "skip",
            "target": None,
            "reason": f"{label} already has {store_max}; this version was already submitted",
        }

    base = max((current, store_max), key=version_tuple)
    target = next_patch(base)
    return {
        "action": "bump",
        "target": target,
        "reason": f"{label} already has {store_max}; bumping {current} to {target}",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome-changed", choices=("true", "false"), default="false")
    parser.add_argument("--firefox-changed", choices=("true", "false"), default="false")
    parser.add_argument(
        "--chrome-already-bumped", choices=("true", "false"), default="false"
    )
    parser.add_argument(
        "--firefox-already-bumped", choices=("true", "false"), default="false"
    )
    parser.add_argument(
        "--dispatch-browser",
        choices=("auto", "chrome", "firefox", "both"),
        default="auto",
    )
    args = parser.parse_args()

    chrome_current = read_manifest_version(CHROME_MANIFEST)
    firefox_current = read_manifest_version(FIREFOX_MANIFEST)
    for label, value in (("Chrome", chrome_current), ("Firefox", firefox_current)):
        if not manifest_version_is_valid(value):
            raise SystemExit(f"{label} manifest version is not X.Y.Z: {value!r}")

    chrome_changed = args.chrome_changed == "true" or args.dispatch_browser in (
        "chrome",
        "both",
    )
    firefox_changed = args.firefox_changed == "true" or args.dispatch_browser in (
        "firefox",
        "both",
    )

    plan: dict[str, dict] = {}

    if chrome_changed:
        store = chrome_store_state() if chrome_configured() else None
        plan["chrome"] = decide(
            chrome_current,
            args.chrome_already_bumped == "true",
            store,
            label="Chrome Web Store",
            pending_first_review=bool(store and store.get("first_review_pending")),
        )
        plan["chrome"]["current"] = chrome_current
        plan["chrome"]["store"] = store
    else:
        plan["chrome"] = {
            "action": "skip",
            "target": None,
            "reason": "no Chrome changes in this update",
            "current": chrome_current,
            "store": None,
        }

    if firefox_changed:
        store = firefox_store_state() if amo_configured() else None
        plan["firefox"] = decide(
            firefox_current,
            args.firefox_already_bumped == "true",
            store,
            label="Mozilla Add-ons",
        )
        plan["firefox"]["current"] = firefox_current
        plan["firefox"]["store"] = store
    else:
        plan["firefox"] = {
            "action": "skip",
            "target": None,
            "reason": "no Firefox changes in this update",
            "current": firefox_current,
            "store": None,
        }

    print(json.dumps(plan, indent=2))

    # A manual dispatch naming a browser is an explicit request: fail rather
    # than silently doing nothing when its credentials are missing.
    errors = []
    if args.dispatch_browser in ("chrome", "both") and plan["chrome"]["action"] == "unconfigured":
        errors.append("Chrome was requested but its store credentials are not configured")
    if args.dispatch_browser in ("firefox", "both") and plan["firefox"]["action"] == "unconfigured":
        errors.append("Firefox was requested but its AMO credentials are not configured")
    for error in errors:
        print(f"::error::{error}", file=sys.stderr)
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
