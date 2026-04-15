# How a Code Push to main-v2 Becomes a Running Container on the Test Server

## Overview

The deployment pipeline has three phases: **CI/CD build** (GitHub Actions), **git sync** (systemd timer on the server), and **auto-deploy** (systemd path watcher on the server). The entire flow is automated with no manual steps required for the test server.

## Phase 1: GitHub Actions CI/CD (cloud)

When code is pushed to the `main-v2` branch, GitHub Actions workflows trigger based on which directories changed:

| Changed path | Workflow file | Docker image |
|---|---|---|
| `newsite/**` | `build-newsite.yml` | `ghcr.io/scgcwebmaster/scgc-newsite` |
| `my-gliding-club/**` | `build-nodejs.yml` | `ghcr.io/scgcwebmaster/scgc-nodejs` |
| `members/**` | `build-vue-members.yml` | `ghcr.io/scgcwebmaster/scgc-vue-members` |
| `ognclient/**` | `build-ognclient.yml` | `ghcr.io/scgcwebmaster/scgc-ognclient` |

Each workflow runs three sequential jobs:

1. **`build`** -- Checks out `main-v2`, auto-increments the version by reading the latest git tag (e.g. `newsite-v1.0.3` -> `1.0.4`), builds the Docker image, saves it as a GitHub Actions artifact, and pushes a new git version tag.

2. **`push`** -- Loads the saved image artifact, logs into `ghcr.io` (GitHub Container Registry), and pushes both `:latest` and `:<version>` tags.

3. **`deploy`** -- Checks out the `deploy-test` branch, uses `sed` to update the image tag in `docker-stack.yml` to the new version, then commits and pushes the change back to `deploy-test`. This is the critical bridge between CI and the server.

## Phase 2: Git Sync on the Test Server (systemd timer)

On the test server (srv3, 43.229.61.116), a **systemd timer** (`scgc-sync-data.timer`) fires every 5 minutes. It triggers `scgc-sync-data.service`, which runs `/usr/local/bin/scgc-sync-data.sh`.

This script:
1. Fetches from the GitHub remote into a bare repo at `~/scgc-monorepo.git`
2. Does a `git pull --ff-only` in two worktrees:
   - `~/docker-server/main-v2` (the main-v2 branch -- for static config, apache files, data)
   - `~/docker-server/deploy-test` (the deploy-test branch -- contains `docker-stack.yml`)

When the deploy job from Phase 1 pushed a new commit to `deploy-test` (with the updated image tag in `docker-stack.yml`), this sync pulls that change down to `~/docker-server/deploy-test/docker-stack.yml`.

## Phase 3: Auto-Deploy on the Test Server (systemd path watcher)

A **systemd path unit** (`scgc-deploy.path`) watches the file:
```
/root/docker-server/deploy-test/docker-stack.yml
```

When the git sync modifies this file, systemd detects the change and triggers `scgc-deploy.service`, which runs `/usr/local/bin/scgc-deploy.sh`. This script:

1. Logs into `ghcr.io` using a stored token at `/root/.ghcr-token`
2. Runs `docker stack deploy -c <stack-file> scgc --with-registry-auth`

Docker Swarm then pulls the new image version from `ghcr.io` and performs a rolling update of the affected service (configured with `order: start-first` so the new container starts before the old one stops).

## End-to-End Timeline

```
Push to main-v2
  |
  v  (seconds)
GitHub Actions: build -> push to ghcr.io -> update deploy-test branch
  |
  v  (up to 5 minutes)
Test server: scgc-sync-data.timer fires, pulls deploy-test
  |
  v  (immediate)
Test server: scgc-deploy.path detects docker-stack.yml change
  |
  v  (seconds)
Test server: docker stack deploy pulls new image, rolling update
  |
  v
New container is running
```

**Typical total latency:** GitHub Actions build time (2-5 min) + sync wait (0-5 min) + container pull/start (~30s) = roughly **3-10 minutes** from push to running container.

## Key Files

| File | Location | Role |
|---|---|---|
| `.github/workflows/build-*.yml` | Repo root | CI/CD: build, push image, update deploy-test |
| `docker-stack.yml` | `deploy-test` branch | Service definitions with pinned image versions |
| `infra/scgc-sync-data.sh` | Server: `/usr/local/bin/` | Pulls latest git changes every 5 min |
| `infra/scgc-sync-data.timer` | Server: `/etc/systemd/system/` | Fires the sync every 5 min |
| `infra/scgc-deploy.sh` | Server: `/usr/local/bin/` | Runs `docker stack deploy` |
| `infra/scgc-deploy.path` | Server: `/etc/systemd/system/` | Watches docker-stack.yml for changes |
| `infra/scgc-quick-deploy.sh` | Server: `/usr/local/bin/` | Manual shortcut: sync + deploy immediately |

## Production Path (for reference)

Production uses the same pattern but with a manual gate. The `promote-to-prod.yml` workflow is triggered manually from the GitHub Actions UI. It copies image versions from `deploy-test` to the `deploy-prod` branch. The production server (srv2) would watch `deploy-prod` instead of `deploy-test`.
