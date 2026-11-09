from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_all_jobs_require_private_capacity():
    for path in WORKFLOWS.glob("*.yml"):
        source = path.read_text(encoding="utf-8")
        assert "ubuntu-" not in source, path.name
        assert "windows-2025" not in source, path.name
        assert "NG_HOSTED_FIRST" not in source, path.name
        workflow = yaml.safe_load(source)
        for job in workflow["jobs"].values():
            if "uses" in job:
                continue
            route = str(job["runs-on"])
            assert any(group in route for group in
                       ("ng-shared-main-jit", "packer-windows", "gvisor-sandbox", "public-fork-jit")), path.name


def test_manual_release_requires_private_pool_and_main():
    source = (WORKFLOWS / "docker.yml").read_text(encoding="utf-8")
    assert "options: [private]" in source
    assert "inputs.runner_pool == 'private'" in source
    assert "github.ref == 'refs/heads/main'" in source


def test_gvisor_smoke_keeps_special_capability_route():
    source = (WORKFLOWS / "gvisor-runner-smoke.yml").read_text(encoding="utf-8")
    assert "options: [private]" in source
    assert "gvisor" in source.lower()


def test_codeql_remains_disabled():
    assert not any("codeql" in path.name.lower() for path in WORKFLOWS.glob("*.yml"))
