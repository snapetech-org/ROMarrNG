from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_release_pipeline_uses_native_hosted_capacity():
    workflow = yaml.safe_load((WORKFLOWS / "docker.yml").read_text())
    for job in workflow["jobs"].values():
        if "uses" in job:
            continue
        if "matrix" in job.get("strategy", {}):
            assert job["runs-on"] == "${{ matrix.runner }}"
            matrix = job["strategy"]["matrix"]
            runners = {x["runner"] for x in matrix["include"]} if "include" in matrix else set(matrix["runner"])
            assert runners == {"ubuntu-24.04", "ubuntu-24.04-arm"}
        else:
            assert job["runs-on"] == "ubuntu-24.04"
    assert "frontend-contracts" in workflow["jobs"]["image"]["needs"]
    windows = yaml.safe_load((WORKFLOWS / "frontend-contracts.yml").read_text())
    assert windows["jobs"]["windows"]["runs-on"] == "windows-2025"


def test_manual_release_requires_public_pool_and_main():
    source = (WORKFLOWS / "docker.yml").read_text()
    assert "options: [public]" in source
    assert "inputs.runner_pool == 'public'" in source
    assert "github.ref == 'refs/heads/main'" in source


def test_fork_validation_uses_disposable_hosted_runner_without_secrets():
    source = (WORKFLOWS / "fork-safe-validation.yml").read_text()
    workflow = yaml.safe_load(source)
    assert workflow["jobs"]["validate"]["runs-on"] == "ubuntu-24.04"
    assert workflow["permissions"] == {"contents": "read"}
    assert "secrets." not in source
    assert "persist-credentials: false" in source


def test_gvisor_smoke_keeps_special_capability_route():
    source = (WORKFLOWS / "gvisor-runner-smoke.yml").read_text()
    assert "options: [private]" in source
    assert "gvisor" in source.lower()


def test_codeql_remains_disabled():
    for path in WORKFLOWS.glob("*.yml"):
        assert "codeql" not in path.name.lower()
        assert "github/codeql-action" not in path.read_text()
