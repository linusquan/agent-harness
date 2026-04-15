# How a Code Push to main-v2 Becomes a Running Container on the Test Server

## End-to-End Flow

The SCGC deployment pipeline is a **pull-based** system with no SSH from CI to the server. It works in five stages:

```
Developer pushes to main-v2
  --> GitHub Actions builds Docker image, pushes to ghcr.io
  --> CI deploy job updates deploy-test branch with new image tag
  --> VPS systemd timer pulls deploy-test every 5 minutes
  --> systemd path watcher detects docker-stack.yml change
  --> scgc-deploy.sh runs: docker stack deploy
```

Below is each stage in detail.

---

## Stage 1: Developer Pushes Code to main-v2

A developer pushes a commit to the `main-v2` branch on GitHub. The push must touch files in a monitored path to trigger the corresponding workflow. For example:

- Changes under `my-gliding-club/**` trigger `build-nodejs.yml`
- Changes under `newsite/**` trigger `build-newsite.yml`
- Changes under the vue members paths trigger `build-vue-members.yml`
- Changes under the ognclient paths trigger `build-ognclient.yml`

Each workflow can also be triggered manually via `workflow_dispatch`.

## Stage 2: GitHub Actions Builds and Pushes the Docker Image

Taking `build-nodejs.yml` as the representative example, the workflow has three sequential jobs:

### Job 1: `build`
1. Checks out `main-v2` with full history (`fetch-depth: 0`).
2. Determines the next version by reading the latest `nodejs-v*` git tag and incrementing the patch number (e.g., `nodejs-v1.0.5` becomes `1.0.6`).
3. Builds the Docker image using `docker/build-push-action` with `no-cache: true`. The image is tagged as both `latest` and the version number (e.g., `ghcr.io/scgcwebmaster/scgc-nodejs:1.0.6`).
4. Saves the image as a tarball artifact for the next job.
5. Creates and pushes the git tag (e.g., `nodejs-v1.0.6`) to the repository.

### Job 2: `push`
1. Downloads the image artifact from the build job.
2. Loads it into the local Docker daemon.
3. Logs into `ghcr.io` using the GitHub token.
4. Tags the image with the version number.
5. Pushes both `latest` and the versioned tag to `ghcr.io/scgcwebmaster/scgc-nodejs`.

### Job 3: `deploy`
1. Checks out the **`deploy-test` branch** (not main-v2).
2. Uses `sed` to replace the image tag in `docker-stack.yml`:
   ```
   sed -i "s|image: ghcr.io/scgcwebmaster/scgc-nodejs:.*|image: ghcr.io/scgcwebmaster/scgc-nodejs:1.0.6|" docker-stack.yml
   ```
3. Commits the change with a message like `deploy: scgc-nodejs:1.0.6`.
4. Pushes to `deploy-test` with retry logic (pull --rebase + push, up to 3 attempts) to handle concurrent builds from different services.

At this point, the `deploy-test` branch on GitHub has an updated `docker-stack.yml` with the new image tag. **No SSH connection is made to the server.**

## Stage 3: VPS Pulls the Updated deploy-test Branch

On srv3 (43.229.61.116), a systemd timer runs every 5 minutes:

**`scgc-sync-data.timer`** (installed at `/etc/systemd/system/scgc-sync-data.timer`):
- Fires 1 minute after boot, then every 5 minutes.
- Triggers `scgc-sync-data.service`.

**`scgc-sync-data.service`** runs `/usr/local/bin/scgc-sync-data.sh`, which:
1. Fetches from origin into the bare repo at `~/scgc-monorepo.git`.
2. Pulls `main-v2` into the `~/docker-server/main-v2` worktree (fast-forward only).
3. Pulls `deploy-test` into the `~/docker-server/deploy-test` worktree (fast-forward only).
4. Logs which branches were updated and what commits changed.

Note: SSH to GitHub uses **port 443** (not 22) because outbound port 22 is blocked on srv3. This is configured in `~/.ssh/config` on the server.

## Stage 4: Path Watcher Detects the Change

**`scgc-deploy.path`** (installed at `/etc/systemd/system/scgc-deploy.path`):
- Watches the file `/root/docker-server/deploy-test/docker-stack.yml`.
- When the file changes (from the git pull in Stage 3), systemd triggers `scgc-deploy.service`.

This is the key mechanism: the path unit creates a reactive link between "git pull updated a file" and "run the deploy script."

## Stage 5: Docker Stack Deploy Runs

**`scgc-deploy.service`** runs `/usr/local/bin/scgc-deploy.sh`, which:

1. Logs that a change was detected.
2. Authenticates to `ghcr.io` using a stored token at `/root/.ghcr-token` so Docker Swarm can pull private images.
3. Runs:
   ```bash
   docker stack deploy -c /root/docker-server/deploy-test/docker-stack.yml scgc --with-registry-auth
   ```
4. Logs the resulting service list.

**Critical detail about working directory**: The deploy command uses the stack file from `deploy-test/` but Docker Swarm resolves bind-mount paths relative to the current working directory. The actual deployment runs from `~/docker-server/main-v2`, so bind mounts like `./scgc-data/public/` resolve to `~/docker-server/main-v2/scgc-data/public/`. This is why `main-v2` has data directories and config files while `deploy-test` only has `docker-stack.yml`.

Docker Swarm then:
- Pulls the new image from `ghcr.io` (if not already cached).
- Performs a rolling update of the affected service, replacing old containers with new ones running the updated image.

---

## Directory Layout on srv3

```
~/scgc-monorepo.git/                  # bare repo (shared git object store)
~/docker-server/
  main-v2/                            # worktree: main-v2 branch
    scgc-data/public/                 #   bind-mounted into nodejs container
    scgc-data/private/                #   bind-mounted into nodejs container
    gliding.com.au/www/               #   bind-mounted into php-apache
    cert/ssl/                         #   bind-mounted into php-apache
    docker-stack.yml                  #   EXISTS but NOT used for deployment
  deploy-test/                        # worktree: deploy-test branch
    docker-stack.yml                  #   THE file used for deployment (watched by systemd)
```

## Timing

- **GitHub Actions**: Build + push + deploy-test commit typically takes 3-8 minutes.
- **VPS sync**: Polls every 5 minutes, so worst case 5 minutes after CI finishes.
- **Path watcher + deploy**: Essentially instant once the file changes.
- **Total end-to-end**: Typically 5-13 minutes from push to running container.

## Production Promotion (Future)

The `promote-to-prod.yml` workflow is manual-only (`workflow_dispatch`). It will copy image tags from `deploy-test` to `deploy-prod`, which srv4 will pull using the same timer/path-watcher/deploy mechanism. This is not yet active.

## Key Design Decisions

1. **Pull-based, not push-based**: The server pulls from GitHub; CI never SSHes into the VPS. This avoids storing server SSH keys in GitHub secrets and reduces the attack surface.
2. **Separation of code and deployment config**: `main-v2` has the source code and data; `deploy-test` has only the stack file with pinned image tags. This means the server only redeploys when an image tag actually changes, not on every code push.
3. **Retry logic for concurrent CI**: Multiple services can build simultaneously. The deploy job retries with `pull --rebase` to handle merge conflicts on `deploy-test`.
4. **Immutable versioning**: Every build gets a unique version tag (auto-incremented patch). No ambiguity about what is deployed -- the exact version is visible in `docker-stack.yml`.
