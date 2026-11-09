#!/usr/bin/env bash
# Run as root after the complete code and virtualenv have been staged.
set -euo pipefail
ROOT="${ROOT:-/opt/romarr}"
DATA="${DATA:-/var/lib/romarr}"
CONF="${CONF:-/etc/romarr}"
UNIT="${UNIT:-/etc/systemd/system/romarr.service}"
ROM_PATH="${ROM_PATH:-/mnt/roms}"
[[ $EUID -eq 0 && "$ROOT" == /* && "$DATA" == /* && "$ROM_PATH" == /* ]]
getent group romarr >/dev/null || groupadd --system romarr
id -u romarr >/dev/null 2>&1 || useradd --system --gid romarr --home-dir "$DATA" --shell /usr/sbin/nologin romarr
install -d -m 0750 -o romarr -g romarr "$DATA"
install -d -m 0750 -o root -g romarr "$CONF" "$CONF/backends"
if [[ ! -e "$ROM_PATH" ]]; then install -d -m 0770 -o romarr -g romarr "$ROM_PATH"; fi
if [[ ! -e "$CONF/romarr.env" ]]; then
  if [[ -f "$ROOT/.env" ]]; then
    install -m 0640 -o root -g romarr "$ROOT/.env" "$CONF/romarr.env"
  else
    printf 'ROMARR_PORT=6868\nLIBRARY_KIND=folder\nLIBRARY_PATH=%s\n' "$ROM_PATH" > "$CONF/romarr.env"
  fi
fi
# State migration only while stopped; never copy an older snapshot over live data.
if [[ -f "$ROOT/romarr.json" && ! -e "$DATA/romarr.json" ]]; then
  install -m 0600 -o romarr -g romarr "$ROOT/romarr.json" "$DATA/romarr.json"
fi
if [[ -d "$ROOT/backends" ]]; then cp -an "$ROOT/backends/." "$CONF/backends/"; fi
if [[ -d "$ROOT/.rom-hub" && ! -e "$DATA/rom-hub" ]]; then
  cp -a "$ROOT/.rom-hub" "$DATA/rom-hub"
  chown -R romarr:romarr "$DATA/rom-hub"
fi
# Replace the legacy defaults; keep unrelated administrator options.
sed -i '/^ROMARR_DATA=/d; /^ROMARR_BACKENDS_DIR=/d; /^ROM_HUB_HOME=/d' "$CONF/romarr.env"
printf '\nROMARR_DATA=%s/romarr.json\nROMARR_BACKENDS_DIR=%s/backends\nROM_HUB_HOME=%s/rom-hub\n' "$DATA" "$CONF" "$DATA" >> "$CONF/romarr.env"
chown -R root:romarr "$CONF"
chmod 0640 "$CONF/romarr.env"
# Application code and dependencies remain owned by root and read-only to romarr.
chown -R root:root "$ROOT"
chmod -R go-w "$ROOT"
cat > "$UNIT" <<EOF
[Unit]
Description=ROMarrNG
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=romarr
Group=romarr
WorkingDirectory=$ROOT/current
EnvironmentFile=$CONF/romarr.env
Environment=HOME=$DATA
ExecStart=$ROOT/current/.venv/bin/python -m romarr
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$DATA $ROM_PATH
UMask=0027
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
