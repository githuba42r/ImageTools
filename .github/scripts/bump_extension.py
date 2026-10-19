#!/usr/bin/env python3
"""Set one browser add-on's manifest version and/or stamp its BUILD_DATE.

Usage:
    bump_extension.py <chrome|firefox> <x.y.z>
    bump_extension.py <chrome|firefox> --build-date-only

The workflow uses the first form when it has to allocate a new store version,
and the second form right before packaging so the popup always shows the real
build time without creating an extra commit.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
BUILD_DATE_RE = re.compile(r"const BUILD_DATE = '[^']*';")


def build_date() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("extension", choices=("chrome", "firefox"))
    parser.add_argument("version", nargs="?")
    parser.add_argument("--build-date-only", action="store_true")
    args = parser.parse_args()

    addon_dir = ROOT / "browser-addons" / args.extension
    manifest_path = addon_dir / "manifest.json"
    popup_path = addon_dir / "popup.js"

    if not args.build_date_only:
        if not args.version or not VERSION_RE.match(args.version):
            parser.error("version must be X.Y.Z")
        manifest = json.loads(manifest_path.read_text())
        manifest["version"] = args.version
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"{args.extension} manifest version -> {args.version}")

    stamp = build_date()
    popup, replacements = BUILD_DATE_RE.subn(
        f"const BUILD_DATE = '{stamp}';", popup_path.read_text()
    )
    if replacements != 1:
        raise SystemExit(
            f"expected exactly one BUILD_DATE line in {popup_path}, found {replacements}"
        )
    popup_path.write_text(popup)
    print(f"{args.extension} BUILD_DATE -> {stamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
