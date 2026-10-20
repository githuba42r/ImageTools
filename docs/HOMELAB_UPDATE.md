# Home lab image updates

The ImageTools container runs on the home lab at `philg@home`:

| | |
| --- | --- |
| Container | `image-tools` |
| Image | `ghcr.io/githuba42r/imagetools:latest` |
| Port | `38081:8081` (Traefik fronts it at `img.a42r.com`) |
| Storage | `/storage/docker/image-tools` → `/app/storage` |
| Managed by | Portainer stack `infrastructure`, service `imagetools` |

The compose file lives inside the Portainer container, not on the host.

## Existing automatic updates

The home lab already runs **Watchtower** with `WATCHTOWER_POLL_INTERVAL=3600`,
so a new `:latest` image is deployed within the hour. It also sends email
notifications and keeps the container's mounts, ports, networks, labels and
restart policy.

## Immediate update

The script runs a one-off, container-scoped Watchtower pass so a release can be
deployed without waiting for the next poll.

From this repository:

```bash
./scripts/update-homelab-image.sh
```

Or on the home lab itself:

```bash
scripts/homelab/update-imagetools.sh
```

Check whether an update is available without changing anything:

```bash
./scripts/update-homelab-image.sh --check
# exit 0 = up to date, exit 10 = a newer image is available
```

The script pulls the image, recreates the container through Watchtower (using
`DOCKER_API_VERSION=1.52`, which this Docker daemon requires), waits for the
health check, and prints the version before and after.

Environment overrides:

```bash
HOMELAB_HOST=philg@home \
CONTAINER=image-tools \
IMAGE=ghcr.io/githuba42r/imagetools:latest \
HEALTH_TIMEOUT=120 \
./scripts/update-homelab-image.sh
```

## Verify

```bash
./scripts/update-homelab-image.sh --check          # should exit 0
ssh philg@home 'curl -s http://localhost:38081/version'
curl -s -o /dev/null -w '%{http_code}\n' https://img.a42r.com/health
```

## Deploying immediately from GitHub Actions (optional)

Watchtower already covers this hourly. If you want the home lab updated the
moment a Docker release completes, add a job after `docker-release` that runs
`scripts/update-homelab-image.sh` over SSH. That needs an SSH key secret for
`philg@home` (e.g. `HOMELAB_SSH_KEY` and `HOMELAB_HOST`) plus a known-hosts
entry; it is not configured.
