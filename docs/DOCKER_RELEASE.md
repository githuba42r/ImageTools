# Docker image releases

`.github/workflows/docker-release.yml` builds and publishes the ImageTools
container whenever the service changes on `master`.

## Trigger

A push to `master` touching any of:

```text
backend/**
frontend/**
mcp-server/**
Dockerfile
.dockerignore
```

`workflow_dispatch` is also available, with a `bump` boolean (default `true`).

## What a run does

1. Bumps `version.json`:
   - `version`: patch + 1 (`1.12.0` → `1.12.1`)
   - `versionCode`: `major * 10000 + minor * 100 + patch` (same XXYYZZ scheme
     as `bump-version.js`)
   - `buildDate`: now, ISO-8601 UTC
2. Commits `chore(docker): bump version to X.Y.Z [skip ci]` and pushes it with
   `GITHUB_TOKEN`. Token-pushed commits do not trigger workflows, so this cannot
   loop.
3. Builds the root `Dockerfile` with `VERSION`/`BUILD_DATE` build args and
   pushes to GHCR:
   ```text
   ghcr.io/githuba42r/imagetools:<version>
   ghcr.io/githuba42r/imagetools:latest
   ```

Only `version.json` is bumped. Android and browser-extension versions are
independent and are not touched. `version.json` is the runtime source of truth:
the Dockerfile copies it to `/version.json`, and the backend serves it from the
`/version` endpoint.

## Pulling the image

```bash
docker pull ghcr.io/githuba42r/imagetools:latest
docker pull ghcr.io/githuba42r/imagetools:1.12.1
```

If the package is private, authenticate first:

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u <username> --password-stdin
```

## Relationship to `release.yml`

`release.yml` still builds and pushes the same image when a `v*` tag is pushed,
as part of a full release. The two workflows are independent; if they overlap,
the last push to `:latest` wins. The tag-triggered build always uses the version
in `version.json`, which the Docker workflow may already have advanced.

## Re-runs and manual runs

- If `HEAD` is already the auto-bump commit (a re-run after a failed build), the
  workflow rebuilds that version instead of bumping again.
- `gh workflow run docker-release.yml -f bump=false` builds the current
  `version.json` without bumping — useful for testing the workflow or
  republishing a version.
- Runs are serialised per ref (`concurrency`), so two pushes cannot race on the
  version bump.
