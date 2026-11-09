#!/usr/bin/env bash
#
# ROMarrNG -- Proxmox LXC installer.
#
# Author: BlizzHacker
# License: MIT
# Source: https://github.com/snapetech-org/ROMarrNG
#
# Run on a Proxmox VE host:
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/snapetech-org/ROMarrNG/main/proxmox/ct/romarr.sh)"
#
# Self-contained on purpose. This script used to source community-scripts'
# build.func, which then fetched `install/<app>.sh` from *its own* repository.
# That framework is built for scripts that live inside community-scripts, and
# ROMarrNG does not, so the fetch 404'd and the documented install command could
# never work (issue #2). It also meant every rename on their side -- ProxmoxVE
# to ProxmoxVED had already happened once -- silently broke our installer.
#
# When ROMarrNG is accepted into community-scripts, their copy lives in their
# repo and uses their framework. This one answers to nobody but us.

set -euo pipefail

APP="ROMarrNG"
APP_PORT="${APP_PORT:-6868}"
REPO="${REPO:-snapetech-org/ROMarrNG}"

# Container defaults. Every one is overridable from the environment, so an
# unattended install is `CTID=123 DISK=8 bash -c "$(curl ...)"`.
CTID="${CTID:-}"
HOSTNAME_="${HOSTNAME_:-romarr}"
DISK="${DISK:-4}"
CPU="${CPU:-1}"
RAM="${RAM:-512}"
BRIDGE="${BRIDGE:-vmbr0}"
STORAGE="${STORAGE:-}"
OSVERSION="${OSVERSION:-13}"
UNPRIVILEGED="${UNPRIVILEGED:-1}"
ROM_PATH="${ROM_PATH:-/mnt/roms}"

RD=$'\033[01;31m'; GN=$'\033[1;92m'; YW=$'\033[33m'; CL=$'\033[m'
msg() { echo -e " ${GN}✔${CL} $1"; }
info() { echo -e " ${YW}➜${CL} $1"; }
die() { echo -e " ${RD}✘ $1${CL}" >&2; exit 1; }

# --- checks, each with an answer rather than a stack trace -----------------

command -v pct >/dev/null 2>&1 || die \
  "'pct' not found. Run this on a Proxmox VE host, not inside a container."
[[ $EUID -eq 0 ]] || die "Run as root."

for tool in curl tar pveam; do
  command -v "$tool" >/dev/null 2>&1 || die "'$tool' is required but missing."
done

# --- pick a container id ---------------------------------------------------

if [[ -z "$CTID" ]]; then
  CTID=$(pvesh get /cluster/nextid 2>/dev/null || echo "")
  [[ -n "$CTID" ]] || die "Could not allocate a container id. Set CTID=<id>."
fi
if pct status "$CTID" >/dev/null 2>&1; then
  die "Container $CTID already exists. Set CTID=<free id>."
fi

# --- storage ---------------------------------------------------------------

# `$3 == "active"` matters: pvesm lists storages that are configured but not
# currently online, and picking one of those fails several steps later inside
# `pct create`, where the error names the storage rather than this choice.
if [[ -z "$STORAGE" ]]; then
  STORAGE=$(pvesm status -content rootdir 2>/dev/null \
            | awk 'NR>1 && $3 == "active" {print $1; exit}')
  [[ -n "$STORAGE" ]] || die \
    "No active storage accepting container root filesystems. Set STORAGE=<name>."
fi

TEMPLATE_STORE=$(pvesm status -content vztmpl 2>/dev/null \
                 | awk 'NR>1 && $3 == "active" {print $1; exit}')
[[ -n "$TEMPLATE_STORE" ]] || die \
  "No active storage accepting container templates (content type 'vztmpl')."

# --- template --------------------------------------------------------------

info "Updating template list"
pveam update >/dev/null 2>&1 || true

TEMPLATE=$(pveam available --section system 2>/dev/null \
  | awk -v v="debian-${OSVERSION}-standard" '$2 ~ v {print $2}' | sort -V | tail -1)
[[ -n "$TEMPLATE" ]] || die \
  "No Debian ${OSVERSION} template offered by this host. Set OSVERSION=<n>."

if ! pveam list "$TEMPLATE_STORE" 2>/dev/null | grep -q "$TEMPLATE"; then
  info "Downloading $TEMPLATE"
  pveam download "$TEMPLATE_STORE" "$TEMPLATE" >/dev/null \
    || die "Failed to download template $TEMPLATE."
fi
msg "Template ready: $TEMPLATE"

# --- create ----------------------------------------------------------------

info "Creating LXC $CTID ($HOSTNAME_)"
pct create "$CTID" "${TEMPLATE_STORE}:vztmpl/${TEMPLATE}" \
  --hostname "$HOSTNAME_" \
  --cores "$CPU" \
  --memory "$RAM" \
  --rootfs "${STORAGE}:${DISK}" \
  --net0 "name=eth0,bridge=${BRIDGE},ip=dhcp" \
  --unprivileged "$UNPRIVILEGED" \
  --features nesting=1 \
  --onboot 1 \
  --tags "arr;emulation" \
  >/dev/null || die "pct create failed."
msg "Created LXC $CTID"

pct start "$CTID" >/dev/null || die "Container $CTID would not start."

# Wait for the network rather than guessing with a sleep: apt fails in a way
# that looks like a broken mirror when DNS is simply not up yet.
info "Waiting for network"
for _ in $(seq 1 30); do
  if pct exec "$CTID" -- getent hosts github.com >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
pct exec "$CTID" -- getent hosts github.com >/dev/null 2>&1 \
  || die "Container $CTID has no working DNS. Check the bridge and DHCP."
msg "Network up"

# --- install ---------------------------------------------------------------

info "Installing dependencies (this takes a minute)"
pct exec "$CTID" -- bash -c "
  set -e
  export DEBIAN_FRONTEND=noninteractive
  # pct exec hands the caller's LANG to a container that has generated no
  # locales, so apt and perl answer with twenty lines of warning that read
  # like a failure. C.UTF-8 always exists and is not one of the ones being
  # complained about.
  export LANG=C.UTF-8 LC_ALL=C.UTF-8
  apt-get update -qq
  # libarchive-tools provides bsdtar, which reads the .7z and .rar archives the
  # disc platforms ship as. Without it every PlayStation, PS2 and Wii import
  # fails on a format it cannot open. Debian's GNU tar is not a substitute.
  apt-get install -y -qq python3-venv python3-pip curl ca-certificates \
    libarchive-tools libseccomp2 git >/dev/null
" || die "Dependency install failed inside container $CTID."
msg "Dependencies installed"

# Install a published release, or an explicitly selected ref. API errors never
# silently substitute development code for the release the operator requested.
info "Fetching $APP"
pct exec "$CTID" -- bash -s -- "$REPO" "${ROMARR_INSTALL_REF:-}" <<'FETCH'
set -euo pipefail
repo="$1"
ref="$2"
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
if [[ -z "$ref" ]]; then
  curl -fsSL --proto '=https' --max-time 60 "https://api.github.com/repos/${repo}/releases/latest" > "$work/release.json"
  ref=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["tag_name"])' "$work/release.json")
fi
[[ "$ref" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
curl -fsSL --proto '=https' --proto-redir '=https' --max-time 300 "https://github.com/${repo}/archive/$ref.tar.gz" -o "$work/source.tar.gz"
mkdir -p /opt/romarr
tar -xzf "$work/source.tar.gz" -C /opt/romarr --strip-components=1 --no-same-owner
if [[ ! -f /opt/romarr/romarr/auth.py || ! -f /opt/romarr/requirements.lock || ! -f /opt/romarr/proxmox/install/configure-service.sh ]]; then
  echo 'The selected release lacks the current installation security contract. Select a supported release, or explicitly opt into main with ROMARR_INSTALL_REF=main.' >&2
  exit 1
fi
test -f /opt/romarr/romarr/auth.py
FETCH
msg "Fetched $APP"

info "Creating virtualenv"
pct exec "$CTID" -- bash -c "
  set -e
  cd /opt/romarr
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet --require-hashes -r requirements-build.lock
  ./.venv/bin/pip install --quiet --no-build-isolation --require-hashes -r requirements.lock
" || die "Python environment setup failed."
msg "Virtualenv ready"

# ROMarrNG starts and serves its UI with none of these reachable, and the
# Settings pages say which are missing -- a first run is never a blank failure.
# Authentication is deliberately not pre-set: the first visit to the web UI
# asks for a password, which is how the install gets claimed.
pct exec "$CTID" -- bash -c "
cat >/opt/romarr/.env <<'ENVEOF'
PROWLARR_URL=
PROWLARR_API_KEY=

QBITTORRENT_URL=
QBITTORRENT_USER=
QBITTORRENT_PASS=

LIBRARY_KIND=romm
LIBRARY_URL=
LIBRARY_USERNAME=
LIBRARY_PASSWORD=

# Where imported ROMs are filed. This must be a path your library server also
# scans, or the import succeeds and the game never appears.
LIBRARY_PATH=${ROM_PATH}
ROMARR_DATA=/opt/romarr/romarr.json
ROMARR_BACKENDS_DIR=/opt/romarr/backends
ROMARR_PORT=${APP_PORT}
LOG_LEVEL=INFO
ENVEOF
chmod 600 /opt/romarr/.env
mkdir -p ${ROM_PATH} /opt/romarr/backends
"

info "Creating service"
pct exec "$CTID" -- bash -c "
  ln -s /opt/romarr /opt/romarr/current
  ROM_PATH='${ROM_PATH}' bash /opt/romarr/proxmox/install/configure-service.sh
  systemctl enable -q --now romarr
"
msg "Service created"

# --- prove it actually came up ---------------------------------------------

info "Waiting for $APP to answer"
UP=0
for _ in $(seq 1 30); do
  if pct exec "$CTID" -- curl -fsS -o /dev/null \
       "http://127.0.0.1:${APP_PORT}/api/health" 2>/dev/null; then
    UP=1
    break
  fi
  sleep 2
done

IP=$(pct exec "$CTID" -- hostname -I 2>/dev/null | awk '{print $1}')

if [[ "$UP" -ne 1 ]]; then
  echo
  die "$APP was installed but is not answering on port ${APP_PORT}.
   Look at:  pct exec ${CTID} -- journalctl -u romarr -n 50 --no-pager"
fi

# Say which version is now running. "Installed" without a version is a report
# nobody can check against a changelog, and this installer deliberately falls
# back from the latest release to main, so which of the two you got matters.
VERSION=$(pct exec "$CTID" -- sed -n 's/^VERSION = "\(.*\)"/\1/p' \
  /opt/romarr/romarr/app.py 2>/dev/null | head -1)

echo
msg "${APP} ${VERSION:-(version unreadable)} is up"
echo -e " ${GN}➜${CL} http://${IP}:${APP_PORT}"
echo -e " ${YW}The first visit asks you to set a password.${CL}"
echo
echo -e " Installed at:  /opt/romarr        Settings:  /etc/romarr/romarr.env"
echo -e " State:         /var/lib/romarr/romarr.json   ${YW}(back this up -- it holds the API key and password)${CL}"
echo -e " ROMs:          ${ROM_PATH}"
echo -e " Logs:          pct exec ${CTID} -- journalctl -u romarr -f"
echo
echo -e " Update later:  pct exec ${CTID} -- bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/${REPO}/main/proxmox/ct/update.sh)\""
