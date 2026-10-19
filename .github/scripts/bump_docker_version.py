#!/usr/bin/env python3
"""Bump version.json for an automatic Docker image release.

The container reads /version.json at runtime (the backend serves it from the
/version endpoint and the frontend fetches that), so version.json is the only
file that has to change for the image version to advance. Android and browser
extension versions are independent and deliberately untouched.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "version.json"
STABLE_RE = re.compile(r"^\d+\.\d+\.\d+$")


def build_date() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def main() -> int:
    data = json.loads(VERSION_FILE.read_text())
    version = data.get("version", "")

    if not STABLE_RE.match(version):
        raise SystemExit(
            f"version.json holds a non-stable version ({version!r}); "
            "automatic Docker releases only bump X.Y.Z"
        )

    major, minor, patch = (int(part) for part in version.split("."))
    patch += 1
    data["version"] = f"{major}.{minor}.{patch}"
    # Same XXYYZZ scheme as bump-version.js so versionCode stays consistent
    # no matter which tool performed the bump.
    data["versionCode"] = major * 10000 + minor * 100 + patch
    data["buildDate"] = build_date()

    VERSION_FILE.write_text(json.dumps(data, indent=2) + "\n")
    print(data["version"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
