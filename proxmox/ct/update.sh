#!/usr/bin/env bash
#
# Update an existing ROMarrNG install, in place.
#
# Run inside the container:
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/snapetech-org/ROMarrNG/main/proxmox/ct/update.sh)"
#
# Or from the Proxmox host:
#   pct exec <ctid> -- bash -c "$(curl -fsSL .../update.sh)"
#
# It reports the version it moved you from and to, refuses to install a build
# that cannot authenticate, and puts the old one back if the new one does not
# answer. Nothing here touches your settings, credentials or history.

set -euo pipefail

REPO="${REPO:-snapetech-org/ROMarrNG}"
ROOT="${ROOT:-/opt/romarr}"

RD=$'\033[01;31m'; GN=$'\033[1;92m'; YW=$'\033[33m'; CL=$'\033[m'
msg() { echo -e " ${GN}✔${CL} $1"; }
info() { echo -e " ${YW}➜${CL} $1"; }
die() { echo -e " ${RD}✘ $1${CL}" >&2; exit 1; }

version_at() {
  sed -n 's/^VERSION = "\(.*\)"/\1/p' "$1/romarr/app.py" 2>/dev/null | head -1
}

[[ $EUID -eq 0 ]] || die "Run as root."
[[ -d "$ROOT" ]] || die "No ROMarrNG installation at ${ROOT}."

BEFORE=$(version_at "$ROOT")
info "Currently installed: ${BEFORE:-unknown}"

# romarr.json holds the request history, the release profile, the API key and
# the password hash. The SQLite sibling holds per-game metadata overrides.
# .env holds service credentials. These are copied to an operator-local backup
# before the install is replaced.
#
# The romarr/ package is copied too, and that copy is not redundant with the
# archive: it is what gets put back when the new build does not come up. An
# update that can only go forwards is not an update, it is a gamble.
STAMP=$(date +%s)
BACKUP="/opt/romarr-backup-${STAMP}"
mkdir -p "$BACKUP"
for keep in romarr.json .env requirements.txt; do
  [[ -f "${ROOT}/${keep}" ]] && cp -a "${ROOT}/${keep}" "${BACKUP}/"
done
# The drop-in backends directory is operator-owned; it is not ours to replace.
[[ -d "${ROOT}/backends" ]] && cp -a "${ROOT}/backends" "${BACKUP}/"
[[ -d "${ROOT}/romarr" ]] && cp -a "${ROOT}/romarr" "${BACKUP}/"
msg "Backed up configuration and the running build to ${BACKUP}"

info "Fetching latest"
answer=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null || true)
# `|| true` because `pipefail` is on and no releases means grep exits 1, which
# would take the whole script with it -- silently, right after "Fetching latest".
url=$(echo "$answer" | grep -o '"tarball_url": *"[^"]*"' | head -1 | cut -d'"' -f4 || true)
SOURCE="latest release"
if [[ -z "$url" ]]; then
  # The release API is unauthenticated and rate-limited at 60/hour per IP, so a
  # throttled answer looks exactly like 'no releases exist'. Saying which it was
  # is the difference between a note and a wrong statement.
  if echo "$answer" | grep -qi 'rate limit'; then
    info "GitHub rate-limited the release lookup; using main"
  else
    info "no published release; using main"
  fi
  SOURCE="main"
  url="https://github.com/${REPO}/archive/refs/heads/main.tar.gz"
fi
curl -fsSL "$url" -o /tmp/romarr-update.tar.gz \
  || die "Download failed from ${REPO}."

# Unpack into a staging directory first. Extracting straight over a running
# install leaves a half-updated tree if the archive is truncated, and there is
# then nothing to roll back to.
STAGE=$(mktemp -d)
tar -xzf /tmp/romarr-update.tar.gz -C "$STAGE" --strip-components=1 \
  || die "Archive did not unpack; the old install is untouched."
rm -f /tmp/romarr-update.tar.gz

# The same refusal the installer makes, for the same reason. The published
# release can lag main by a long way -- v0.7.0 was tagged before authentication
# existed -- and an *update* that silently replaces an authenticated build with
# an open one is worse than an install that does, because the operator has
# already decided this thing is safe to leave running.
if [[ ! -f "${STAGE}/romarr/auth.py" ]]; then
  rm -rf "$STAGE"
  die "The ${SOURCE} of ${REPO} has no romarr/auth.py -- it predates
   authentication, and installing it would leave this ROMarrNG answering
   anyone who reaches the port. Nothing was changed."
fi

AFTER=$(version_at "$STAGE")
if [[ -n "$BEFORE" && "$BEFORE" == "$AFTER" ]]; then
  info "Already on ${BEFORE} (from ${SOURCE}); reinstalling it anyway"
else
  info "Updating ${BEFORE:-unknown} -> ${AFTER:-unknown} (from ${SOURCE})"
fi

# Only now. Every check above can fail, and each one used to happen after the
# service had already been stopped -- so a download that 404'd or an archive
# that would not unpack left ROMarrNG down for a reason that had nothing to do
# with ROMarrNG.
systemctl stop romarr 2>/dev/null || true

# SQLite's online backup API gives a consistent snapshot even when ROMarr was
# writing metadata while the release was downloaded and staged. Make this
# snapshot only after stopping the service, immediately before replacement.
STATE_PATH="${ROMARR_DATA:-}"
if [[ -z "$STATE_PATH" && -f "${ROOT}/.env" ]]; then
  STATE_PATH=$(sed -n 's/^[[:space:]]*ROMARR_DATA[[:space:]]*=[[:space:]]*//p' \
    "${ROOT}/.env" | tail -1)
  STATE_PATH=${STATE_PATH#\"}; STATE_PATH=${STATE_PATH%\"}
  STATE_PATH=${STATE_PATH#\'}; STATE_PATH=${STATE_PATH%\'}
fi
STATE_PATH="${STATE_PATH:-${ROOT}/romarr.json}"
[[ "$STATE_PATH" = /* ]] || STATE_PATH="${ROOT}/${STATE_PATH}"
METADATA_DB_PATH=$(python3 - "$STATE_PATH" <<'PY'
from pathlib import Path
import sys
state = Path(sys.argv[1])
print(state.with_name(state.stem + ".library-metadata.sqlite3"))
PY
)
if [[ -f "$METADATA_DB_PATH" ]]; then
  if ! python3 - "$METADATA_DB_PATH" "${BACKUP}/library-metadata.sqlite3" <<'PY'
import sqlite3
import sys

with sqlite3.connect(sys.argv[1], timeout=10) as source:
    with sqlite3.connect(sys.argv[2]) as destination:
        source.backup(destination)
PY
  then
    systemctl start romarr
    die "Could not safely back up ${METADATA_DB_PATH}; the service was restarted and the install is unchanged."
  fi
  printf '%s\n' "$METADATA_DB_PATH" > "${BACKUP}/library-metadata.path"
fi
msg "Backed up state and the running build to ${BACKUP}"

# The package directory is replaced, not merged. `cp -a` over the top leaves
# any module that upstream deleted sitting in an importable package forever,
# which is how a version reports itself as new while still running old code.
rm -rf "${ROOT}/romarr"
cp -a "$STAGE"/. "$ROOT"/
rm -rf "$STAGE"

for keep in romarr.json .env; do
  [[ -f "${BACKUP}/${keep}" ]] && cp -a "${BACKUP}/${keep}" "${ROOT}/"
done
[[ -d "${BACKUP}/backends" ]] && cp -a "${BACKUP}/backends" "${ROOT}/"
msg "Unpacked"

info "Updating dependencies"
"${ROOT}/.venv/bin/pip" install --quiet --upgrade -r "${ROOT}/requirements.txt" \
  || die "Dependency update failed. State is in ${BACKUP}."
msg "Dependencies updated"

systemctl start romarr

PORT=$(grep -oP '(?<=^ROMARR_PORT=)\d+' "${ROOT}/.env" 2>/dev/null || echo 6868)
for _ in $(seq 1 20); do
  if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/api/health" 2>/dev/null; then
    msg "ROMarrNG ${AFTER:-unknown} is up on port ${PORT} (was ${BEFORE:-unknown})"
    echo
    echo " Rolled forward. The previous build is in ${BACKUP} if you want it"
    echo " back; delete that directory once you are happy."
    exit 0
  fi
  sleep 2
done

# It did not answer. Put back what was working rather than leaving a container
# that is down and a directory of files the operator has to reassemble by hand.
info "New build did not answer -- rolling back to ${BEFORE:-the previous build}"
systemctl stop romarr 2>/dev/null || true
if [[ -d "${BACKUP}/romarr" ]]; then
  rm -rf "${ROOT}/romarr"
  cp -a "${BACKUP}/romarr" "${ROOT}/"
  if [[ -f "${BACKUP}/library-metadata.sqlite3" \
        && -f "${BACKUP}/library-metadata.path" ]]; then
    metadata_path=$(cat "${BACKUP}/library-metadata.path")
    mkdir -p "$(dirname "$metadata_path")"
    cp -a "${BACKUP}/library-metadata.sqlite3" "$metadata_path"
  fi
  systemctl start romarr
  for _ in $(seq 1 20); do
    if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/api/health" 2>/dev/null; then
      die "Update failed and was rolled back. ROMarrNG ${BEFORE:-unknown} is
   running again. The build that would not start is not kept -- fetch it
   again once the cause is known.
   Look at:  journalctl -u romarr -n 50 --no-pager"
    fi
    sleep 2
  done
fi

die "ROMarrNG did not come back up, and the rollback did not either. State is
   in ${BACKUP} -- romarr.json, .env and any saved metadata snapshot are there.
   Look at:  journalctl -u romarr -n 50 --no-pager"
