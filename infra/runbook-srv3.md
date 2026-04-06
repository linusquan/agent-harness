# Server Runbook: srv3.gliding.com.au

**Last updated:** 2026-04-06

---

## Server Specs

| Property | Value |
|---|---|
| Hostname | srv3.gliding.com.au |
| Provider | BinaryLane (Sydney, au-east-2) |
| OS | Ubuntu 24.04.4 LTS |
| vCPU / RAM / Disk | 1 / 1.5 GB / 20 GB NVMe |
| Public IP | 43.229.61.116 |
| Panel | https://www.binarylane.com.au/mpanel/manage/srv3.gliding.com.au |

---

## Initial Server Setup

Run these steps immediately after provisioning a new BinaryLane server. The goal is to replace password-based SSH with key-only access.

### Step 1: Generate a dedicated SSH key (local machine)

```bash
ssh-keygen -t ed25519 -C "scgc-binarylane" -f ~/.ssh/id_binarylane -N ""
```

This creates:
- `~/.ssh/id_binarylane` — private key (never share)
- `~/.ssh/id_binarylane.pub` — public key (goes on the server)

### Step 2: Copy the public key to the server

**Option A — ssh-copy-id (if password SSH works):**

```bash
ssh-copy-id -i ~/.ssh/id_binarylane.pub root@<server-ip>
```

Enter the root password from the BinaryLane panel when prompted.

**Option B — BinaryLane web terminal (if ssh-copy-id fails):**

1. Log into BinaryLane panel → server page → web terminal
2. Get the public key contents: `cat ~/.ssh/id_binarylane.pub`
3. In the web terminal, run:

```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo "<paste-public-key-here>" > /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

> **Note:** The BinaryLane web terminal (VNC) can be difficult to paste into. If pasting fails, use Playwright or ssh-copy-id instead.

### Step 3: Add the server host key to known_hosts

```bash
ssh-keyscan -t ed25519 <server-ip> >> ~/.ssh/known_hosts
```

### Step 4: Verify key-based SSH works

```bash
ssh -i ~/.ssh/id_binarylane root@<server-ip> "echo 'SSH key auth OK'"
```

You should see `SSH key auth OK`. If this fails, do NOT proceed to Step 5 — you will lock yourself out.

### Step 5: Disable password authentication

```bash
ssh -i ~/.ssh/id_binarylane root@<server-ip> \
  "sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && \
   systemctl restart ssh && \
   echo 'Password auth disabled'"
```

> Ubuntu 24.04 uses `systemctl restart ssh` (not `sshd`).

### Step 6: Verify password login is rejected

```bash
ssh -o PasswordAuthentication=yes \
    -o PubkeyAuthentication=no \
    -o BatchMode=yes \
    -o ConnectTimeout=5 \
    root@<server-ip> "echo 'FAIL: password still works'" 2>&1 \
  || echo "PASS: password auth rejected"
```

Expected output: `PASS: password auth rejected`

### Step 7: Add SSH config alias (optional)

Add to `~/.ssh/config`:

```
Host srv3
    HostName <server-ip>
    User root
    IdentityFile ~/.ssh/id_binarylane
```

Then connect with just: `ssh srv3`

### Step 8: Run the server init script

Installs Docker, Docker Compose, configures UFW firewall (ports 22, 80, 443), and sets the timezone.

```bash
ssh -i ~/.ssh/id_binarylane root@<server-ip> 'bash -s' < infra/init-server.sh
```

**What the script does:**
1. Updates system packages (`apt upgrade`)
2. Installs Docker CE + Docker Compose plugin from the official Docker repo
3. Enables and starts the Docker service
4. Installs and configures UFW firewall:
   - Port 22 (SSH)
   - Port 80 (HTTP)
   - Port 443 (HTTPS)
   - All other ports blocked
5. Sets timezone to `Australia/Sydney`

> The script is idempotent — safe to run again if interrupted.

---

## Lockout Recovery

If you lose SSH key access:

1. Log into BinaryLane panel → web terminal (VNC console, no SSH needed)
2. Re-enable password auth temporarily:
   ```bash
   sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
   systemctl restart ssh
   ```
3. Use `ssh-copy-id` to install a new key
4. Verify key login works
5. Disable password auth again (Step 5 above)

```
ssh -i ~/.ssh/id_binarylane root@43.229.61.116

```