# Production Server Migration Plan
# srv2 → srv4 (new BinaryLane VPS)

**Created:** 2026-04-18
**Status:** Pre-migration planning

---

## Overview

Migrate production from `srv2.gliding.com.au` (old) to a fresh BinaryLane VPS (`srv4.gliding.com.au`).
The new server mirrors `srv3` (test) in setup but differs in: domain, SSL certs, secrets, and adds a MariaDB backup cron job.

---

## Checklist Summary

| Phase | Step | Status |
|-------|------|--------|
| **A. Provision** | 1. Create BinaryLane VPS | ☐ |
| **A. Provision** | 2. SSH key setup | ☐ |
| **A. Provision** | 3. Run init-server.sh | ☐ |
| **A. Provision** | 4. BinaryLane port blocking | ☐ |
| **B. Git Sync** | 5. Create GitHub deploy key on server | ☐ |
| **B. Git Sync** | 6. Add deploy key to GitHub | ☐ |
| **B. Git Sync** | 7. Create deploy-prod branch | ☐ |
| **B. Git Sync** | 8. Bare clone + worktrees | ☐ |
| **B. Git Sync** | 9. Install sync + deploy systemd units | ☐ |
| **C. Stack** | 10. Docker Swarm init | ☐ |
| **C. Stack** | 11. GHCR login | ☐ |
| **C. Stack** | 12. SSL certs in place | ☐ |
| **C. Stack** | 13. Docker secrets | ☐ |
| **C. Stack** | 14. Pre-deployment directories | ☐ |
| **C. Stack** | 15. DB backup cron job | ☐ |
| **C. Stack** | 16. CI deploy-prod workflow jobs | ☐ |
| **D. Cutover** | 17. Lock old server (maintenance mode) | ☐ |
| **D. Cutover** | 18. Final MariaDB dump from srv2 | ☐ |
| **D. Cutover** | 19. Transfer + import DB on new server | ☐ |
| **D. Cutover** | 20. Smoke test new server via IP | ☐ |
| **D. Cutover** | 21. Update DNS (Route 53) | ☐ |
| **D. Cutover** | 22. Verify gliding.com.au resolves correctly | ☐ |
| **D. Cutover** | 23. Decommission srv2 | ☐ |

---

## Phase A: Provision Server

### Step 1 — Create BinaryLane VPS

- Provider: BinaryLane (Sydney, au-east-2)
- OS: Ubuntu 24.04 LTS
- Spec: ≥ 2 vCPU / 2 GB RAM / 40 GB NVMe (upgrade from srv3's 1.5 GB)
- Hostname: `srv4.gliding.com.au` (set in panel)
- Panel: https://home.binarylane.com.au

Record the new IP here: **`___.___.___.___ `**

After provisioning, set reverse DNS in BinaryLane panel → `srv4.gliding.com.au`.

Enable port blocking in panel: allow ports 22, 80, 443 only.

### Step 2 — SSH Key Setup

Reuse the existing `~/.ssh/id_binarylane` key (already on local machine).

```bash
# Copy public key to new server (use root password from BinaryLane panel)
ssh-copy-id -i ~/.ssh/id_binarylane.pub root@<NEW_IP>

# Add to known_hosts
ssh-keyscan -t ed25519 <NEW_IP> >> ~/.ssh/known_hosts

# Verify key auth works BEFORE disabling password
ssh -i ~/.ssh/id_binarylane root@<NEW_IP> "echo 'SSH key auth OK'"

# Disable password auth
ssh -i ~/.ssh/id_binarylane root@<NEW_IP> \
  "sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
   systemctl restart ssh && echo 'Password auth disabled'"

# Verify password is rejected
ssh -o PasswordAuthentication=yes -o PubkeyAuthentication=no \
    -o BatchMode=yes -o ConnectTimeout=5 \
    root@<NEW_IP> "echo FAIL" 2>&1 || echo "PASS: password rejected"
```

Add SSH config alias locally (`~/.ssh/config`):
```
Host srv4
    HostName <NEW_IP>
    User root
    IdentityFile ~/.ssh/id_binarylane
```

### Step 3 — Run init-server.sh

```bash
ssh -i ~/.ssh/id_binarylane root@<NEW_IP> 'bash -s' < infra/init-server.sh
```

Installs: Docker CE, UFW (22/80/443), unattended-upgrades, timezone Australia/Sydney.

### Step 4 — Verify BinaryLane Port Blocking

In BinaryLane panel → Port Blocking → allow: 22, 80, 443.
UFW and BinaryLane port blocking are independent — both must allow the ports.

---

## Phase B: Git Sync Setup

### Step 5 — Create GitHub Deploy Key on Server

```bash
ssh srv4
ssh-keygen -t ed25519 -C "scgc-binarylane-prod" -f ~/.ssh/id_ed25519_github -N ""
cat ~/.ssh/id_ed25519_github.pub
```

Copy the public key output — needed for Step 6.

Configure SSH to use port 443 for GitHub (port 22 outbound is blocked on BinaryLane):
```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
EOF
```

Test:
```bash
ssh -T git@github.com  # expect: "successfully authenticated"
```

### Step 6 — Add Deploy Key to GitHub

1. Go to: https://github.com/SCGCWebmaster/scgc-monorepo/settings/keys
2. Click "Add deploy key"
3. Title: `srv4-prod`
4. Paste the public key from Step 5
5. Read-only access (no write access needed)

### Step 7 — Create deploy-prod Branch

From local machine:

```bash
cd src/

# Create deploy-prod from deploy-test as a base (same structure, different image tags)
git checkout deploy-test
git checkout -b deploy-prod
git push origin deploy-prod
git checkout main-v2  # return to main branch
```

Review `docker-stack.yml` on `deploy-prod` and update:
- Remove `EMAIL_SUBJECT_PREFIX=[TEST srv3]` env var (or set to empty)
- Pin Payments: will use production keys (set via Docker secrets, not stack file)
- SSL cert paths: update to match production cert filenames (see Phase C Step 12)

### Step 8 — Bare Clone + Worktrees

```bash
ssh srv4

REPO_URL="git@github.com:SCGCWebmaster/scgc-monorepo.git"

# Bare clone
git clone --bare "$REPO_URL" ~/scgc-monorepo.git

# Worktrees
git -C ~/scgc-monorepo.git worktree add ~/docker-server/main-v2 main-v2
git -C ~/scgc-monorepo.git worktree add ~/docker-server/deploy-prod deploy-prod

# Verify
ls ~/docker-server/
```

### Step 9 — Install Systemd Sync + Deploy Units

Copy service files to server:
```bash
scp src/infra/scgc-sync-data.sh    srv4:/usr/local/bin/scgc-sync-data.sh
scp src/infra/scgc-sync-data.service srv4:/etc/systemd/system/
scp src/infra/scgc-sync-data.timer   srv4:/etc/systemd/system/
scp src/infra/scgc-deploy.sh         srv4:/usr/local/bin/scgc-deploy.sh
scp src/infra/scgc-deploy.service    srv4:/etc/systemd/system/
scp src/infra/scgc-deploy.path       srv4:/etc/systemd/system/
```

**Edit sync script on server** to track `deploy-prod` instead of `deploy-test`:
```bash
ssh srv4
sed -i 's/deploy-test/deploy-prod/g' /usr/local/bin/scgc-sync-data.sh
sed -i 's|docker-server/deploy-test|docker-server/deploy-prod|g' /usr/local/bin/scgc-sync-data.sh
```

**Edit deploy.path on server** to watch deploy-prod:
```bash
sed -i 's|deploy-test|deploy-prod|g' /etc/systemd/system/scgc-deploy.path
```

**Edit deploy.sh on server** to use deploy-prod stack:
```bash
sed -i 's|deploy-test|deploy-prod|g' /usr/local/bin/scgc-deploy.sh
```

Make scripts executable and enable:
```bash
chmod +x /usr/local/bin/scgc-sync-data.sh /usr/local/bin/scgc-deploy.sh
systemctl daemon-reload
systemctl enable --now scgc-sync-data.timer
systemctl enable scgc-deploy.path scgc-deploy.service

# Trigger first sync
systemctl start scgc-sync-data.service
journalctl -u scgc-sync-data.service -f
```

---

## Phase C: Stack Setup

### Step 10 — Docker Swarm Init

```bash
ssh srv4
docker swarm init
```

### Step 11 — GHCR Login (Pull Credentials)

```bash
ssh srv4

# Use a GitHub PAT with read:packages scope
echo "<GITHUB_PAT>" | docker login ghcr.io -u SCGCWebmaster --password-stdin
```

The deploy script needs this login persisted. Verify:
```bash
cat ~/.docker/config.json | grep ghcr
```

### Step 12 — SSL Certificates

Production uses a **commercial CA cert** (not Let's Encrypt).
Certs are stored in git at `cert/ssl/` on `main-v2`:

| File | Description |
|------|-------------|
| `cert/ssl/private.key` | Private key |
| `cert/ssl/wwwglidingcom.crt` | Server certificate |
| `cert/ssl/intermediate.crt` | CA chain/intermediate |

These are already available via the `main-v2` worktree on the server:
```bash
ssh srv4
ls ~/docker-server/main-v2/cert/ssl/
```

The `deploy-prod` docker-stack.yml must bind-mount:
```yaml
- /root/docker-server/main-v2/cert/ssl:/etc/apache2/cert:ro
```

**Check cert expiry:**
```bash
openssl x509 -enddate -noout -in ~/docker-server/main-v2/cert/ssl/wwwglidingcom.crt
```

If the cert is within 30 days of expiry, renew before cutover (see ssl-cert-management.md).

### Step 13 — Docker Secrets

Run the secrets setup script on the server. Use **production values** (not test values).

```bash
ssh srv4

# MariaDB root password
echo -n "<PROD_DB_ROOT_PASSWORD>" | docker secret create db_root_password -

# Pin Payments — PRODUCTION keys (not sandbox)
echo -n "<PROD_PIN_KEY>" | docker secret create pin_key -
echo -n "<PROD_PIN_PUB_KEY>" | docker secret create pin_pub_key -
echo -n "https://pay.pinpayments.com/..." | docker secret create pin_url -
echo -n "api.pinpayments.com" | docker secret create pin_api_url -

# Database URL
echo -n "mysql://fls:<PROD_DB_PASS>@mariadb/fls" | docker secret create database_url -

# S3/R2 Backup — production Cloudflare R2 credentials
echo -n "<PROD_S3_ACCESS_KEY_ID>" | docker secret create s3_access_key_id -
echo -n "<PROD_S3_SECRET_ACCESS_KEY>" | docker secret create s3_secret_access_key -

# Email
echo -n "<PROD_SMTP_URL>" | docker secret create smtp_url -
echo -n "flogincoming@gliding.com.au" | docker secret create imap_username -
echo -n "<PROD_IMAP_PASSWORD>" | docker secret create imap_password -

# NAIPS
echo -n "<NAIPS_PASSWORD>" | docker secret create naips_password -

# LLM (chatbot)
echo -n "<LLM_API_KEY>" | docker secret create llm_api_key -
echo -n "https://api.openai.com/v1" | docker secret create llm_base_url -
echo -n "<LLM_MODEL>" | docker secret create llm_model -

# Verify
docker secret ls
```

> Current test values are in `.artifacts/infra/create-secrets-test-prod.sh` — never use test keys on production.

### Step 14 — Pre-deployment Directories

Some dirs are gitignored but must exist before the stack starts:

```bash
ssh srv4
cd ~/docker-server/main-v2
mkdir -p gliding.com.au/www/administration/usercontent
mkdir -p logs
mkdir -p dbDump
chmod 777 logs and usercontent
```

### Step 15 — MariaDB Backup Cron Job

can be done later
```


### Step 16 — CI Workflows: Add deploy-prod Jobs

Update all three workflow files to add production deploy jobs:
- `src/.github/workflows/build-newsite.yml`
- `src/.github/workflows/build-nodejs.yml`
- `src/.github/workflows/build-vue-members.yml`

Each needs a new `deploy-prod` job (mirror of the existing `deploy` job but targeting `deploy-prod` branch):
```yaml
deploy-prod:
  runs-on: ubuntu-latest
  needs: [build, push]
  permissions:
    contents: write
  steps:
    - uses: actions/checkout@v4
      with:
        ref: deploy-prod
        fetch-depth: 1
    - name: Update image tag
      run: |
        IMAGE="${{ env.IMAGE_NAME }}"
        VERSION="${{ needs.build.outputs.version }}"
        sed -i "s|image: ${IMAGE}:.*|image: ${IMAGE}:${VERSION}|" docker-stack.yml
    - name: Commit and push
      run: |
        git config user.name "github-actions[bot]"
        git config user.email "github-actions[bot]@users.noreply.github.com"
        git add docker-stack.yml
        git diff --cached --quiet && echo "No changes" && exit 0
        git commit -m "deploy: ${IMAGE_NAME##*/}:${{ needs.build.outputs.version }}"
        for i in 1 2 3; do
          git pull --rebase origin deploy-prod && git push origin deploy-prod && break
          sleep 2
        done
```

---

## Phase D: Cutover

> **Critical:** Do this during low-traffic hours (e.g. Sunday 3–5am AEST). Estimated downtime: ~15 minutes.

### Step 17 — Lock Old Server (Maintenance Mode)

Put the PHP/Apache container on srv2 into maintenance mode to stop new writes to the database.

```bash
ssh root@srv2.gliding.com.au

# Option A: Scale down nodejs (stops new bookings/payments)
docker service scale scgc_nodejs=0

# Option B: Add maintenance page to Apache (less disruptive if needed longer)
# (implement as needed)
```

Note the exact timestamp — all data up to this point must be in the final backup.

### Step 18 — Final MariaDB Dump from srv2

```bash
ssh root@srv2.gliding.com.au

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER=$(docker ps -qf name=scgc_mariadb)

# Dump to host
docker exec $CONTAINER \
  mysqldump -u fls -p<DB_PASS> fls \
  > /tmp/fls-prod-${TIMESTAMP}.sql

echo "Dump size: $(du -sh /tmp/fls-prod-${TIMESTAMP}.sql)"
```

### Step 19 — Transfer + Import DB on New Server

```bash
# Transfer from srv2 to local machine first
scp root@srv2.gliding.com.au:/tmp/fls-prod-*.sql /tmp/

# Transfer to new server
scp /tmp/fls-prod-*.sql srv4:/tmp/

# Import on new server
ssh srv4

DUMP_FILE=$(ls /tmp/fls-prod-*.sql | tail -1)
CONTAINER=$(docker ps -qf name=scgc_mariadb)

# Copy dump into container and import
docker cp "$DUMP_FILE" $CONTAINER:/tmp/import.sql
docker exec $CONTAINER \
  mysql -u fls -p<PROD_DB_PASS> fls < /tmp/import.sql

echo "Import complete"

# Verify row counts
docker exec $CONTAINER \
  mysql -u fls -p<PROD_DB_PASS> fls \
  -e "SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema='fls' ORDER BY table_rows DESC LIMIT 10;"
```

### Step 20 — Smoke Test New Server via IP

Before changing DNS, test the new server directly by IP (or via `/etc/hosts`):

```bash
# Add temporary entry to local /etc/hosts
echo "<NEW_IP> gliding.com.au www.gliding.com.au" | sudo tee -a /etc/hosts

# Test
curl -sk https://gliding.com.au/ | head -20
# Check: members login, booking page loads, static assets load

# Remove hosts entry when done
sudo sed -i '/<NEW_IP>/d' /etc/hosts
```

### Step 21 — Update DNS (Route 53)

Update the A record for `gliding.com.au` and `www.gliding.com.au` to point to the new server IP.

```bash
NEW_IP="<NEW_IP>"

aws --profile scgc-infra route53 change-resource-record-sets \
  --hosted-zone-id Z3I44JK6JWF2I4 \
  --change-batch "{
    \"Changes\": [
      {
        \"Action\": \"UPSERT\",
        \"ResourceRecordSet\": {
          \"Name\": \"gliding.com.au\",
          \"Type\": \"A\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"${NEW_IP}\"}]
        }
      },
      {
        \"Action\": \"UPSERT\",
        \"ResourceRecordSet\": {
          \"Name\": \"www.gliding.com.au\",
          \"Type\": \"A\",
          \"TTL\": 60,
          \"ResourceRecords\": [{\"Value\": \"${NEW_IP}\"}]
        }
      }
    ]
  }"
```

> TTL set to 60s for fast propagation during cutover. Increase to 300 after confirmed stable.

### Step 22 — Verify DNS + Site

```bash
# Check propagation (may take up to 60s)
dig gliding.com.au A +short
dig www.gliding.com.au A +short

# Verify site loads correctly
curl -I https://gliding.com.au/
curl -I https://www.gliding.com.au/

# Check SSL cert is valid and for the right domain
echo | openssl s_client -connect gliding.com.au:443 2>/dev/null | openssl x509 -noout -subject -dates
```

Functional checks:
- [ ] Homepage loads
- [ ] Members login works
- [ ] Booking/payment flow works (use a test transaction)
- [ ] Emails send correctly (check logs: `docker service logs scgc_nodejs`)
- [ ] SSL cert valid (no browser warning)

Once stable, raise DNS TTL back to 300:
```bash
aws --profile scgc-infra route53 change-resource-record-sets \
  --hosted-zone-id Z3I44JK6JWF2I4 \
  --change-batch '{"Changes":[{"Action":"UPSERT","ResourceRecordSet":{"Name":"gliding.com.au","Type":"A","TTL":300,"ResourceRecords":[{"Value":"<NEW_IP>"}]}},{"Action":"UPSERT","ResourceRecordSet":{"Name":"www.gliding.com.au","Type":"A","TTL":300,"ResourceRecords":[{"Value":"<NEW_IP>"}]}}]}'
```

### Step 23 — Decommission srv2

Only after confirming new server is fully operational for ≥ 24 hours.

1. Take a final BinaryLane snapshot of srv2 (keep for 30 days as a fallback)
2. In BinaryLane panel: cancel/destroy srv2
3. Remove `srv2.gliding.com.au` from DNS if it has its own A record
4. Archive old deploy runbooks — note srv2 is decommissioned

---

## Key Differences: srv3 (test) vs srv4 (prod)

| Aspect | srv3 (test) | srv4 (prod) |
|--------|-------------|-------------|
| Hostname | srv3.gliding.com.au | srv4.gliding.com.au |
| Domain served | test.gliding.com.au | gliding.com.au, www.gliding.com.au |
| SSL certs | Let's Encrypt (auto-renew) | Commercial CA (manual renew, in git) |
| Pin Payments | Sandbox keys | Production keys |
| Deploy branch | deploy-test | deploy-prod |
| Sync tracks | main-v2 + deploy-test | main-v2 + deploy-prod |
| `EMAIL_SUBJECT_PREFIX` | `[TEST srv3]` | (unset) |
| DB backup cron | No | Yes — daily to R2 at 3am |
| Server size | 1 vCPU / 1.5 GB | ≥ 2 vCPU / 2 GB (recommended) |

---

## Rollback Plan

If cutover fails or critical issues are found after DNS change:

1. **Repoint DNS back to srv2** (same Route 53 command, use old IP)
2. DNS propagates within 60s (TTL was set low during cutover)
3. Re-enable nodejs on srv2: `docker service scale scgc_nodejs=1`
4. Investigate issue on srv4 before re-attempting

**Maximum exposure window:** 60 seconds of DNS propagation time.
