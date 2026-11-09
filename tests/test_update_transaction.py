"""Exercise the real updater with temporary trees and offline system stubs."""
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest


@pytest.mark.parametrize("failure", ["release", "pip", "configure", "health", "none"])
def test_upgrade_failure_preserves_live_state_and_running_release(tmp_path, failure):
    if os.geteuid() != 0:
        pytest.skip("updater requires root; CI runs this in a disposable root namespace")
    root = tmp_path / "install"
    old = root / "old"
    source = tmp_path / "fixture"
    data = tmp_path / "data"
    conf = tmp_path / "conf"
    commands = tmp_path / "commands"
    for path in (old / "romarr", source / "romarr", source / "proxmox/install", data, conf, commands):
        path.mkdir(parents=True, exist_ok=True)
    (root / "current").symlink_to(old, target_is_directory=True)
    (old / "romarr/app.py").write_text('VERSION = "old"\n')
    (source / "romarr/app.py").write_text('VERSION = "new"\n')
    (source / "romarr/auth.py").touch()
    for name in ("requirements.lock", "requirements-build.lock"):
        (source / name).touch()
    (source / "proxmox/install/configure-service.sh").write_text(
        '#!/bin/bash\nset -eu\necho migrated > "$UNIT"\n'
        '[[ "$FAILURE" != configure ]]\n')
    archive = tmp_path / "release.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        output.add(source, arcname="fixture")
    unit = tmp_path / "romarr.service"
    unit.write_text("old unit\n")
    state = data / "romarr.json"
    state.write_text("before stop\n")
    log = tmp_path / "operations"

    def stub(name, content):
        path = commands / name
        path.write_text(content)
        path.chmod(0o755)

    stub("curl", '''#!/bin/bash
set -eu
if [[ "$*" == *releases/latest* ]]; then
  [[ "$FAILURE" != release ]] || exit 22
  echo '{"tag_name":"v1.0.0"}'
else
  while [[ "$1" != -o ]]; do shift; done
  cp "$ARCHIVE" "$2"
fi
''')
    stub("python3", f'''#!{sys.executable}
import os, pathlib, sys
if sys.argv[1:3] == ["-m", "venv"]:
    folder = pathlib.Path(sys.argv[3]) / "bin"
    folder.mkdir(parents=True)
    for name, script in {{
        "pip": '#!/bin/bash\\n[[ "$FAILURE" != pip ]]\\n',
        "python": '#!/bin/bash\\nif [[ "$*" == *healthcheck* ]]; then [[ "$FAILURE" != health ]]; fi\\n',
    }}.items():
        path = folder / name
        path.write_text(script)
        path.chmod(0o755)
else:
    os.execv({sys.executable!r}, [{sys.executable!r}] + sys.argv[1:])
''')
    stub("systemctl", '''#!/bin/bash
set -eu
echo "$*" >> "$OPERATIONS"
if [[ "$1" == stop ]]; then echo "committed at stop" > "$DATA/romarr.json"; fi
''')
    stub("sleep", "#!/bin/bash\nexit 0\n")
    env = {**os.environ, "PATH": str(commands) + os.pathsep + os.environ["PATH"],
           "ROOT": str(root), "DATA": str(data), "CONF": str(conf), "UNIT": str(unit),
           "FAILURE": failure, "ARCHIVE": str(archive), "OPERATIONS": str(log)}
    env.pop("ROMARR_UPDATE_REF", None)
    script = Path(__file__).resolve().parents[1] / "proxmox/ct/update.sh"
    result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=15)
    assert (result.returncode == 0) == (failure == "none"), result.stdout + result.stderr
    if failure in {"release", "pip"}:
        assert not log.exists(), "service was stopped before its replacement was ready"
        assert state.read_text() == "before stop\n"
    else:
        assert state.read_text() == "committed at stop\n", "rollback restored stale data"
        snapshots = list((root / "backups").rglob("romarr.json"))
        assert snapshots and all(p.read_text() == "committed at stop\n" for p in snapshots)
        assert "start romarr" in log.read_text()
    if failure == "none":
        assert (root / "current").resolve() != old
        assert "migrated" in unit.read_text()
    else:
        assert (root / "current").resolve() == old
        assert unit.read_text() == ("migrated\n" if failure == "health" else "old unit\n")
