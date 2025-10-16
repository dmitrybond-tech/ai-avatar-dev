#!/usr/bin/env bash
set -euo pipefail

USER_NAME="${USER_NAME:-deploy}"
VPS_USER="${VPS_USER:-root}"
VPS_IP="${VPS_IP:-}"
if [[ -z "$VPS_IP" ]]; then
  echo "Set VPS_IP env var, e.g. VPS_IP=203.0.113.42"; exit 1
fi

sudo apt-get update -y
sudo apt-get install -y autossh

for unit in miniapp-front-tunnel.service miniapp-api-tunnel.service; do
  tmp="/tmp/${unit}"
  sed -e "s|User=deploy|User=${USER_NAME}|g" \
      -e "s|/home/deploy|/home/${USER_NAME}|g" \
      -e "s|Environment=VPS_USER=<SET_ME>|Environment=VPS_USER=${VPS_USER}|g" \
      -e "s|Environment=VPS_IP=<SET_ME>|Environment=VPS_IP=${VPS_IP}|g" \
      "infra/systemd/${unit}" > "${tmp}"
  sudo mv "${tmp}" "/etc/systemd/system/${unit}"
done

sudo systemctl daemon-reload
sudo systemctl enable --now miniapp-front-tunnel miniapp-api-tunnel
systemctl --no-pager --full status miniapp-front-tunnel miniapp-api-tunnel

