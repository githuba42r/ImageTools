#!/usr/bin/env bash
#
# Force an immediate update of the ImageTools container on the home lab.
#
# The home lab already runs Watchtower with WATCHTOWER_POLL_INTERVAL=3600,
# so a new :latest image is picked up within the hour. This script runs a
# one-off, container-scoped Watchtower pass so a release can be deployed now.
#
# The container is managed by a Portainer stack (project "infrastructure",
# service "imagetools"); its compose file lives inside the Portainer
# container. Watchtower recreates the container with the same image, mounts,
# ports, networks, labels and restart policy, so no compose file is needed.
#
# Usage (on the home lab):
#   update-imagetools.sh            # pull and recreate now
#   update-imagetools.sh --check    # exit 0 if current, 10 if an update exists
#
# Environment overrides:
#   CONTAINER=image-tools
#   IMAGE=ghcr.io/githuba42r/imagetools:latest
#   WATCHTOWER_IMAGE=containrrr/watchtower
#   HEALTH_TIMEOUT=120
set -euo pipefail

CONTAINER="${CONTAINER:-image-tools}"
IMAGE="${IMAGE:-ghcr.io/githuba42r/imagetools:latest}"
WATCHTOWER_IMAGE="${WATCHTOWER_IMAGE:-containrrr/watchtower}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
# The scheduled Watchtower container sets this too; without it the one-off
# client defaults to API 1.25, which the daemon rejects.
DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.52}"

log() { printf '[imagetools-update] %s\n' "$*"; }

version_label() {
  docker inspect "$CONTAINER" --format '{{ index .Config.Labels "org.opencontainers.image.version" }}' 2>/dev/null || true
}

health() {
  docker inspect "$CONTAINER" \
    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
    2>/dev/null || true
}

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Container $CONTAINER not found" >&2
  exit 1
fi

# Avoid racing the scheduled Watchtower pass or another manual run.
exec 9>/tmp/imagetools-update.lock
if ! flock -n 9; then
  log "another update is already running"
  exit 0
fi

before="$(version_label)"
log "container: $CONTAINER"
log "image:     $IMAGE"
log "before:    ${before:-unknown} ($(health))"

if [ "${1:-}" = "--check" ]; then
  running_image="$(docker inspect "$CONTAINER" --format '{{.Image}}')"
  running_digest="$(docker image inspect "$running_image" --format '{{join .RepoDigests ","}}' | tr ',' '\n' | head -1)"
  remote_digest="$(docker buildx imagetools inspect "$IMAGE" --format '{{.Manifest.Digest}}' 2>/dev/null || true)"
  if [ -n "$remote_digest" ] && [[ "$running_digest" == *"$remote_digest"* ]]; then
    log "up to date ($remote_digest)"
    exit 0
  fi
  log "update available (running=${running_digest:-unknown} remote=${remote_digest:-unknown})"
  exit 10
fi

log "pulling $IMAGE"
docker pull "$IMAGE"

log "running a scoped Watchtower pass"
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e WATCHTOWER_CLEANUP=true \
  -e DOCKER_API_VERSION="$DOCKER_API_VERSION" \
  "$WATCHTOWER_IMAGE" \
  --run-once "$CONTAINER"

log "waiting for $CONTAINER to become healthy (up to ${HEALTH_TIMEOUT}s)"
deadline=$((SECONDS + HEALTH_TIMEOUT))
while [ "$SECONDS" -lt "$deadline" ]; do
  state="$(health)"
  if [ "$state" = "healthy" ]; then
    break
  fi
  sleep 3
done

after="$(version_label)"
state="$(health)"
log "after:     ${after:-unknown} ($state)"

if [ "$state" != "healthy" ]; then
  log "warning: container is not healthy after the update"
  exit 1
fi

log "done"
