#!/usr/bin/env bash
# Stage code AND dependencies while the old process runs. Stop only to migrate
# state and switch a single symlink. Every post-stop failure restores the old unit.
set -euo pipefail
REPO="${REPO:-snapetech-org/ROMarrNG}"
ROOT="${ROOT:-/opt/romarr}"
UNIT="${UNIT:-/etc/systemd/system/romarr.service}"
DATA="${DATA:-/var/lib/romarr}"
CONF="${CONF:-/etc/romarr}"
die() { echo "$*" >&2; exit 1; }
version_at() { sed -n 's/^VERSION = "\(.*\)"/\1/p' "$1/romarr/app.py" | head -1; }
[[ $EUID -eq 0 && -d "$ROOT" ]] || { echo 'Run as root on an installed container.' >&2; exit 1; }
[[ "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]
exec 9>"$ROOT/.update.lock"
flock -n 9 || { echo 'Another update is running.' >&2; exit 1; }
install -d -m 0755 "$ROOT/releases"
STAGE=$(mktemp -d "$ROOT/releases/release-XXXXXXXX")
WORK=$(mktemp -d)
CONFIGURED=0
STOPPED=0
SWITCHED=0
OLD=$(readlink -f "$ROOT/current" 2>/dev/null || true)
[[ -d "$OLD" ]] || OLD="$ROOT"
BEFORE=$(version_at "$OLD")
cp -a "$UNIT" "$WORK/romarr.service"
cleanup() {
  result=$?
  trap - EXIT
  if (( result != 0 && STOPPED )); then
    systemctl stop romarr || true
    if (( SWITCHED )); then ln -s "$OLD" "$ROOT/.rollback-current"; mv -Tf "$ROOT/.rollback-current" "$ROOT/current"; fi
    # A migrated install keeps the new unprivileged unit and live state path;
    # only the code/venv symlink rolls back. Before migration completes use
    # the untouched previous unit.
    if (( ! CONFIGURED )); then cp -a "$WORK/romarr.service" "$UNIT"; fi
    systemctl daemon-reload
    systemctl start romarr || true
    echo 'Update failed; rolling back code and dependencies. Current state was preserved.' >&2
  fi
  rm -rf "$WORK"
  if (( ! SWITCHED )); then rm -rf "$STAGE"; fi
  exit "$result"
}
trap cleanup EXIT
# Any API/rate-limit/network error fails closed. Main is never an implicit fallback.
if [[ -n "${ROMARR_UPDATE_REF:-}" ]]; then
  [[ "$ROMARR_UPDATE_REF" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
  REF="$ROMARR_UPDATE_REF"
else
  curl --fail --silent --show-error --proto '=https' --max-time 60 "https://api.github.com/repos/${REPO}/releases/latest" > "$WORK/release.json"
  REF=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tag_name"])' "$WORK/release.json")
  [[ "$REF" =~ ^v[0-9][A-Za-z0-9._-]*$ ]]
fi
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --max-time 300 "https://github.com/${REPO}/archive/$REF.tar.gz" -o "$WORK/release.tar.gz"
tar -xzf "$WORK/release.tar.gz" -C "$STAGE" --strip-components=1 --no-same-owner
[[ -f "$STAGE/romarr/auth.py" && -f "$STAGE/requirements.lock" && -f "$STAGE/proxmox/install/configure-service.sh" ]]
python3 -m venv "$STAGE/.venv"
"$STAGE/.venv/bin/pip" install --require-hashes -r "$STAGE/requirements-build.lock"
"$STAGE/.venv/bin/pip" install --no-build-isolation --require-hashes -r "$STAGE/requirements.lock"
(cd "$STAGE" && .venv/bin/python -c 'import romarr.app, rom_hub')
AFTER=$(version_at "$STAGE")
# Custom backends are preserved by configure-service.sh, outside the release tree.
# Backup happens AFTER the service stops; never restore stale live-state copies.
systemctl stop romarr
STOPPED=1
BACKUP="$ROOT/backups/$(date +%s)-$$"
install -d -m 0700 "$BACKUP"
for state in "$ROOT/romarr.json" "$DATA/romarr.json" "$CONF/romarr.env" "$ROOT/.env"; do
  if [[ -f "$state" ]]; then cp -a --parents "$state" "$BACKUP/"; fi
done
for base in "$ROOT" "$DATA"; do
  for state in "$base/romarr-catalog.sqlite3" "$base/"*.library-metadata.sqlite3; do
    [[ -f "$state" ]] || continue
    cp -a --parents "$state" "$BACKUP/"
    for suffix in -journal -wal -shm; do
      [[ ! -f "$state$suffix" ]] || cp -a --parents "$state$suffix" "$BACKUP/"
    done
  done
done
ln -s "$STAGE" "$ROOT/.next-current"
mv -Tf "$ROOT/.next-current" "$ROOT/current"
SWITCHED=1
ROOT="$ROOT" DATA="$DATA" CONF="$CONF" UNIT="$UNIT" bash "$STAGE/proxmox/install/configure-service.sh"
CONFIGURED=1
systemctl start romarr
for _ in $(seq 1 20); do
  if (cd "$ROOT/current" && ROMARR_ENV_FILE="$CONF/romarr.env" .venv/bin/python -c 'import os, shlex; from pathlib import Path; from romarr.healthcheck import check
for line in Path(os.environ["ROMARR_ENV_FILE"]).read_text().splitlines():
 if line.strip() and not line.lstrip().startswith("#") and "=" in line:
  k,v=line.split("=",1); parts=shlex.split(v); os.environ[k]=parts[0] if parts else ""
check()') 2>/dev/null; then
    echo "ROMarrNG $AFTER (was $BEFORE; ref $REF) is healthy. Previous build: $OLD; stopped-state backup: $BACKUP"
    exit 0
  fi
  sleep 2
done
echo 'New service did not pass its health check.' >&2
exit 1
