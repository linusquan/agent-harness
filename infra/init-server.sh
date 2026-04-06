#!/usr/bin/env bash
#
# SCGC Server Init Script
# Run once on a fresh Ubuntu 24.04 BinaryLane server after SSH key setup.
#
# Usage:
#   ssh -i ~/.ssh/id_binarylane root@<server-ip> 'bash -s' < infra/init-server.sh
#
set -euo pipefail

echo "=== SCGC Server Init ==="
echo "OS: $(lsb_release -ds)"
echo ""

# ── 1. System updates ──────────────────────────────────────────────
echo "[1/5] Updating system packages..."
apt-get update -qq
apt-get upgrade -y -qq
echo "Done."

# ── 2. Install Docker (official repo) ──────────────────────────────
echo "[2/5] Installing Docker..."
if command -v docker &>/dev/null; then
  echo "Docker already installed: $(docker --version)"
else
  apt-get install -y -qq ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  systemctl enable docker
  systemctl start docker
  echo "Installed: $(docker --version)"
fi

# ── 3. Install Docker Compose (plugin is included above, verify) ───
echo "[3/5] Verifying Docker Compose..."
docker compose version
echo "Done."

# ── 4. Configure UFW firewall ──────────────────────────────────────
echo "[4/5] Configuring firewall (UFW)..."
apt-get install -y -qq ufw

# Allow SSH first (never lock yourself out)
ufw allow 22/tcp comment "SSH"

# Web traffic
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"

# Enable UFW (non-interactive)
echo "y" | ufw enable
ufw status verbose
echo "Done."

# ── 5. Unattended security upgrades ────────────────────────────────
echo "[5/6] Enabling unattended security upgrades..."
apt-get install -y -qq unattended-upgrades
# Enable automatic security updates (non-interactive)
echo 'Unattended-Upgrade::Automatic-Reboot "false";' > /etc/apt/apt.conf.d/51auto-upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades
systemctl enable unattended-upgrades
echo "Done."

# ── 6. Set timezone ────────────────────────────────────────────────
echo "[6/6] Setting timezone to Australia/Sydney..."
timedatectl set-timezone Australia/Sydney
echo "Timezone: $(timedatectl show -p Timezone --value)"

echo ""
echo "=== Init complete ==="
echo "Docker:   $(docker --version)"
echo "Compose:  $(docker compose version)"
echo "Firewall: $(ufw status | head -1)"
echo "Timezone: $(date +%Z)"
