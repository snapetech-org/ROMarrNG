from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_release_pipeline_uses_hosted_runners():
    workflow = yaml.safe_load((WORKFLOWS / "docker.yml").read_text(encoding="utf-8"))
    for name in (
        "release-notes",
        "test",
        "acquisition-proof",
        "image",
        "image_publish",
        "image-browser",
        "image_browser_publish",
        "verify-stable-image-tags",
        "release",
    ):
        assert workflow["jobs"][name]["runs-on"] == "ubuntu-24.04"


def test_manual_release_requires_public_pool_and_main():
    source = (WORKFLOWS / "docker.yml").read_text(encoding="utf-8")
    assert "options: [public]" in source
    assert "inputs.runner_pool == 'public'" in source
    assert "github.ref == 'refs/heads/main'" in source


def test_ordinary_workflows_do_not_require_private_capacity():
    for path in WORKFLOWS.glob("*.yml"):
        if path.name == "gvisor-runner-smoke.yml":
            continue
        source = path.read_text(encoding="utf-8")
        assert "private-jit-only" not in source, path.name
        assert "options: [private]" not in source, path.name
        assert '"group":"ng-shared-main-jit"' not in source, path.name


def test_gvisor_smoke_keeps_special_capability_route():
    source = (WORKFLOWS / "gvisor-runner-smoke.yml").read_text(encoding="utf-8")
    assert "options: [private]" in source
    assert "gvisor" in source.lower()


def test_codeql_remains_disabled():
    assert not any("codeql" in path.name.lower() for path in WORKFLOWS.glob("*.yml"))
