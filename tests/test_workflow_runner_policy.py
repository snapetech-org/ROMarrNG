import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"
TRUSTED_MAIN_WORKFLOWS = {
    "docker.yml",
    "dependency-review.yml",
    "semgrep-community.yml",
    "trivy-filesystem.yml",
}
GVISOR_SANDBOX_RUNNER = {"group": "gvisor-sandbox", "labels": "gvisor-sandbox"}
PUBLIC_FORK_RUNNER = {
    "group": "public-fork-jit",
    "labels": [
        "self-hosted",
        "linux",
        "x64",
        "public-pr-romarrng",
        "ng-public-run-${{ github.run_id }}",
    ],
}
PUBLIC_FORK_CHILD_PREFIX = (
    "snapetech-org/ROMarrNG/.github/workflows/fork-safe-validation.yml@"
)


def _workflow_events(document: dict) -> object:
    events = document.get("on")
    if events is None and True in document:
        events = document[True]
    return events


def _is_approved_public_fork_wrapper(
    workflow: Path, job_name: str, job: dict, document: dict
) -> bool:
    events = _workflow_events(document)
    pull_request = events.get("pull_request") if isinstance(events, dict) else None
    uses = job.get("uses")
    if not isinstance(uses, str) or not uses.startswith(PUBLIC_FORK_CHILD_PREFIX):
        return False
    pin = uses.removeprefix(PUBLIC_FORK_CHILD_PREFIX)
    return (
        workflow.name == "public-fork-pr.yml"
        and job_name == "validate"
        and document.get("permissions") == {"contents": "read"}
        and isinstance(pull_request, dict)
        and pull_request.get("branches") == ["main"]
        and pull_request.get("types")
        == ["opened", "synchronize", "reopened", "ready_for_review"]
        and len(pin) == 40
        and all(character in "0123456789abcdef" for character in pin)
        and all(
            condition in job.get("if", "")
            for condition in (
                "github.event.pull_request.head.repo.fork == true",
                "github.event.pull_request.base.repo.full_name == 'snapetech-org/ROMarrNG'",
                "github.event.pull_request.base.ref == 'main'",
            )
        )
    )


def _is_approved_public_fork_runner(
    workflow: Path, job_name: str, job: dict, document: dict
) -> bool:
    events = _workflow_events(document)
    return (
        workflow.name == "fork-safe-validation.yml"
        and job_name == "validate"
        and events == {"workflow_call": None}
        and document.get("permissions") == {"contents": "read"}
        and job.get("permissions") == {"contents": "read"}
        and job.get("runs-on") == PUBLIC_FORK_RUNNER
        and all(
            condition in job.get("if", "")
            for condition in (
                "github.event.pull_request.head.repo.fork == true",
                "github.event.pull_request.base.repo.full_name == 'snapetech-org/ROMarrNG'",
                "github.event.pull_request.base.ref == 'main'",
            )
        )
    )


def _is_approved_gvisor_sandbox_job(
    workflow: Path, job_name: str, job: dict, document: dict
) -> bool:
    workflow_events = document.get("on")
    if workflow_events is None and True in document:
        workflow_events = document[True]
    return (
        workflow.name == "gvisor-runner-smoke.yml"
        and job_name == "smoke"
        and document.get("name") == "gVisor runner smoke"
        and workflow_events == {"workflow_dispatch": None}
        and document.get("permissions") == {}
        and set(job) == {"if", "timeout-minutes", "runs-on", "steps"}
        and job.get("if") == "github.ref == 'refs/heads/main'"
        and job.get("timeout-minutes") == 5
        and job.get("runs-on") == GVISOR_SANDBOX_RUNNER
    )


TRUSTED_MAIN_JOB_LABELS = {
    "docker.yml": {
        "release-notes": "gha-{0}-release-notes",
        "test": "gha-{0}-test",
        "acquisition-proof": "gha-{0}-{1}-acquisition-proof",
        "image": "gha-{0}-image",
        "image-browser": "gha-{0}-image-browser",
        "image_publish": "gha-{0}-image_publish",
        "image_browser_publish": "gha-{0}-image_browser_publish",
        "verify-stable-image-tags": "gha-{0}-verify-stable-image-tags",
        "release": "gha-{0}-release",
        "legacy-aliases": "gha-{0}-legacy-aliases",
    },
    "dependency-review.yml": {"dependency-review": "gha-{0}-dependency-review"},
    "semgrep-community.yml": {"semgrep": "gha-{0}-semgrep"},
    "trivy-filesystem.yml": {"trivy": "gha-{0}-trivy"},
}
OWNER_PR_JOB_LABELS = {
    "release-notes": "gha-{0}-release-notes",
    "test": "gha-{0}-test",
    "acquisition-proof": "gha-{0}-acquisition-{matrix.dockerfile}",
    "image": "gha-{0}-image",
    "image-browser": "gha-{0}-image-browser",
    "security-review": "gha-{0}-security-review",
}
OWNER_PR_GATE = (
    "github.event_name == 'workflow_dispatch' && "
    "(github.actor == 'snapetech' || github.actor == 'github-actions[bot]') && "
    "inputs.pr_number != '' && inputs.pr_sha != '' && inputs.pr_base_sha != '' && "
    "inputs.target_run_id != '' && github.ref == 'refs/heads/main'"
)
OWNER_PR_SPECIAL_GATES = {
    "dispatch-owner-pr": (
        "github.event_name == 'pull_request_target' && "
        "github.actor == 'snapetech' && "
        "github.event.pull_request.user.login == 'snapetech' && "
        "github.event.pull_request.head.repo.full_name == github.repository && "
        "github.event.pull_request.head.repo.id == github.repository_id && "
        "github.event.pull_request.base.ref == 'main'"
    ),
    "report-owner-pr-check": OWNER_PR_GATE,
}
OWNER_PR_SPECIAL_LABELS = {
    "dispatch-owner-pr": "gha-{0}-owner-pr-dispatcher",
    "report-owner-pr-check": "gha-{0}-owner-pr-reporter",
}
MAIN_OR_TAG_ROUTE = (
    "contains(fromJSON('[\"push\",\"workflow_dispatch\",\"schedule\","
    "\"release\",\"repository_dispatch\"]'), github.event_name) && "
    "(github.ref == 'refs/heads/main' || (github.ref_type == 'tag' && "
    "startsWith(github.ref_name, 'v')))"
)
SCAN_ROUTE = (
    "(github.event_name == 'push' && github.ref_type == 'tag' && "
    "startsWith(github.ref_name, 'v')) || "
    "(github.event_name == 'workflow_dispatch' && "
    "github.ref == 'refs/heads/main')"
)
DEPENDENCY_REVIEW_GATE = (
    "github.event_name == 'workflow_dispatch' && "
    "github.actor == 'snapetech' && github.ref == 'refs/heads/main'"
)
LEGACY_ALIASES_ROUTE = (
    "((github.event_name == 'push' && github.ref_type == 'tag' && "
    "startsWith(github.ref_name, 'v')) || "
    "(github.event_name == 'workflow_dispatch' && "
    "(github.actor == 'snapetech' || github.actor == 'github-actions[bot]') && "
    "github.ref == 'refs/heads/main' && inputs.pr_number == '' && "
    "inputs.pr_sha == '' && inputs.pr_base_sha == '' && inputs.target_run_id == ''))"
)


def _runner_payload(job_label: str, *, matrix: bool = False) -> str:
    matrix_arg = ", strategy.job-index" if matrix else ""
    return (
        "fromJSON(format('{{\"group\":\"ng-shared-main-jit\","
        "\"labels\":[\"self-hosted\",\"linux\",\"x64\","
        "\"ng-shared-main-romarrng\",\"ng-main-run-{0}\",\""
        + job_label
        + "\"]}}', github.run_id"
        + matrix_arg
        + "))"
    )


def _is_approved_owner_pr_runner(workflow: Path, job_name: str, runner: object) -> bool:
    if workflow.name != "docker.yml" or not isinstance(runner, str):
        return False
    gate = OWNER_PR_SPECIAL_GATES.get(job_name)
    suffix = OWNER_PR_SPECIAL_LABELS.get(job_name)
    if gate is None or suffix is None:
        return False
    expected = "${{ (" + gate + ") && " + _runner_payload(suffix) + " }}"
    return runner == expected


def _is_trusted_main_runner(
    workflow: Path, job_name: str, job: dict, runner: object
) -> bool:
    if workflow.name not in TRUSTED_MAIN_WORKFLOWS or not isinstance(runner, str):
        return False
    if not (runner.startswith("${{ ") and runner.endswith(" }}")):
        return False

    job_label = TRUSTED_MAIN_JOB_LABELS.get(workflow.name, {}).get(job_name)
    if job_label is None:
        return False
    matrix_runner = job_name == "acquisition-proof"
    if workflow.name in {"semgrep-community.yml", "trivy-filesystem.yml"}:
        expected = "${{ (" + SCAN_ROUTE + ") && " + _runner_payload(job_label) + " }}"
        return job.get("if") == SCAN_ROUTE and runner == expected
    if workflow.name == "dependency-review.yml":
        expected = (
            "${{ ("
            + DEPENDENCY_REVIEW_GATE
            + ") && "
            + _runner_payload(job_label)
            + " }}"
        )
        return job.get("if") == DEPENDENCY_REVIEW_GATE and runner == expected

    route_condition = (
        LEGACY_ALIASES_ROUTE
        if job_name == "legacy-aliases"
        else MAIN_OR_TAG_ROUTE
    )
    normal_route = (
        f"(({route_condition}) && "
        f"{_runner_payload(job_label, matrix=matrix_runner)})"
    )
    if job_name not in OWNER_PR_JOB_LABELS:
        return runner == "${{ " + normal_route + " }}"

    if job_name == "acquisition-proof":
        owner_route = (
            "((matrix.dockerfile == 'Dockerfile' && "
            + _runner_payload("gha-{0}-acquisition-dockerfile")
            + ") || (matrix.dockerfile == 'Dockerfile.browser' && "
            + _runner_payload("gha-{0}-acquisition-browser")
            + "))"
        )
    else:
        owner_route = _runner_payload(OWNER_PR_JOB_LABELS[job_name])
    expected = (
        "${{ ("
        + OWNER_PR_GATE
        + ") && "
        + owner_route
        + " || (!("
        + OWNER_PR_GATE
        + ") && "
        + normal_route
        + ") }}"
    )
    return runner == expected


def _runner_policy_violations(workflow_dir: Path) -> list[str]:
    workflow_files = sorted(
        path
        for suffix in ("*.yml", "*.yaml")
        for path in workflow_dir.glob(suffix)
        if path.is_file()
    )
    if not workflow_files:
        return ["workflow files must be present"]

    violations: list[str] = []
    runner_count = 0
    for workflow in workflow_files:
        document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            violations.append(f"{workflow.name}: workflow must be a YAML mapping")
            continue

        jobs = document.get("jobs")
        if not isinstance(jobs, dict):
            violations.append(f"{workflow.name}: jobs must be a YAML mapping")
            continue

        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                violations.append(
                    f"{workflow.name}/{job_name}: job must be a YAML mapping"
                )
                continue
            if "uses" in job and "runs-on" not in job:
                if _is_approved_public_fork_wrapper(workflow, job_name, job, document):
                    continue
                violations.append(
                    f"{workflow.name}/{job_name}: reusable workflow runner is not "
                    "visible in this file"
                )
                continue

            runner = job.get("runs-on")
            runner_count += 1
            location = f"{workflow.name}/{job_name}"
            if _is_approved_gvisor_sandbox_job(workflow, job_name, job, document):
                continue
            if _is_approved_public_fork_runner(workflow, job_name, job, document):
                continue
            if _is_approved_owner_pr_runner(workflow, job_name, runner):
                continue
            if _is_trusted_main_runner(workflow, job_name, job, runner):
                continue
            violations.append(
                f"{location}: unsupported runner assignment {runner!r}; "
                "workflows must use approved private JIT runners; hosted fallback is forbidden"
            )

    if runner_count == 0 and not violations:
        violations.append("no checked-in workflow runner assignments were found")
    return violations


class WorkflowRunnerPolicyTests(unittest.TestCase):
    def test_main_and_release_buildkit_use_the_proxy_without_hosted_fallback(self) -> None:
        workflow = yaml.safe_load(
            (WORKFLOW_DIR / "docker.yml").read_text(encoding="utf-8")
        )
        image_job = workflow["jobs"]["image"]
        proxy_gate = image_job["env"]["BUILDKIT_EGRESS_PROXY"]
        self.assertIn(OWNER_PR_GATE, proxy_gate)
        self.assertIn(MAIN_OR_TAG_ROUTE, proxy_gate)
        self.assertIn("'http://10.0.2.100:3128' || ''", proxy_gate)
        self.assertNotIn("NG_HOSTED_FIRST", proxy_gate)
        self.assertNotIn("ubuntu-latest", str(image_job["runs-on"]))
        buildx = next(
            step
            for step in image_job["steps"]
            if "setup-buildx-action" in step.get("uses", "")
        )
        driver_opts = buildx["with"]["driver-opts"]
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            self.assertIn(
                f"env.{key}=${{{{ env.BUILDKIT_EGRESS_PROXY }}}}", driver_opts
            )
        self.assertNotIn(",", driver_opts)

        builds = [
            step
            for step in image_job["steps"]
            if "build-push-action" in step.get("uses", "")
        ]
        self.assertEqual(len(builds), 2)
        for build in builds:
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                self.assertIn(
                    f"{key}=${{{{ env.BUILDKIT_EGRESS_PROXY }}}}",
                    build["with"]["build-args"],
                )
            for key in ("NO_PROXY", "no_proxy"):
                self.assertIn(
                    f"{key}=localhost,127.0.0.1",
                    build["with"]["build-args"],
                )

        for job_name in ("image-browser", "image_publish", "image_browser_publish"):
            with self.subTest(job=job_name):
                job = workflow["jobs"][job_name]
                if job_name == "image-browser":
                    self.assertIn(OWNER_PR_GATE, job["if"])
                    self.assertIn("gha-{0}-image-browser", job["runs-on"])
                    self.assertNotIn("ubuntu-latest", job["runs-on"])
                    self.assertIn("BUILDKIT_EGRESS_PROXY", job.get("env", {}))
                    self.assertIn(OWNER_PR_GATE, job["env"]["BUILDKIT_EGRESS_PROXY"])
                else:
                    self.assertNotIn("BUILDKIT_EGRESS_PROXY", job.get("env", {}))
                    self.assertNotIn("10.0.2.100:3128", str(job))

    def test_publishers_and_release_use_the_trusted_runner_route(self) -> None:
        workflow = yaml.safe_load(
            (WORKFLOW_DIR / "docker.yml").read_text(encoding="utf-8")
        )

        for job_name in ("image_publish", "image_browser_publish", "release"):
            with self.subTest(job=job_name):
                self.assertTrue(
                    _is_trusted_main_runner(
                        Path("docker.yml"),
                        job_name,
                        workflow["jobs"][job_name],
                        workflow["jobs"][job_name]["runs-on"],
                    )
                )

    def test_product_images_publish_only_on_pushed_version_tags(self) -> None:
        workflow = yaml.safe_load(
            (WORKFLOW_DIR / "docker.yml").read_text(encoding="utf-8")
        )

        for job_name in ("image_publish", "image_browser_publish", "release"):
            with self.subTest(job=job_name):
                condition = workflow["jobs"][job_name]["if"]
                self.assertIn("github.event_name == 'push'", condition)
                self.assertIn("github.ref_type == 'tag'", condition)
                self.assertIn("startsWith(github.ref_name, 'v')", condition)
                self.assertNotIn("refs/heads/main", condition)
                self.assertNotIn("workflow_dispatch", condition)

        image_build = workflow["jobs"]["image"]
        build_steps = [
            step
            for step in image_build["steps"]
            if "build-push-action" in step.get("uses", "")
        ]
        self.assertTrue(build_steps)
        self.assertTrue(
            all(step["with"].get("push", False) is False for step in build_steps)
        )

    def test_dependency_review_runs_use_run_scoped_non_cancelling_concurrency(self) -> None:
        workflow = yaml.safe_load(
            (WORKFLOW_DIR / "dependency-review.yml").read_text(encoding="utf-8")
        )

        self.assertEqual(
            workflow["concurrency"],
            {
                "group": "${{ github.workflow }}-${{ github.run_id }}",
                "cancel-in-progress": False,
            },
        )

    def test_workflows_use_private_jit_except_the_exact_sandbox_smoke_job(self) -> None:
        self.assertEqual(
            _runner_policy_violations(WORKFLOW_DIR),
            [],
            "only exact private JIT routes and the gVisor sandbox smoke job may select runner groups",
        )

    def test_trusted_main_runner_is_scoped_to_this_project_and_run(self) -> None:
        condition = MAIN_OR_TAG_ROUTE
        valid_runner = (
            "${{ ((" + condition + ") && "
            + _runner_payload("gha-{0}-image_publish")
            + ") }}"
        )

        self.assertTrue(
            _is_trusted_main_runner(Path("docker.yml"), "image_publish", {}, valid_runner)
        )
        self.assertFalse(
            _is_trusted_main_runner(Path("unrelated.yml"), "image_publish", {}, valid_runner)
        )
        self.assertFalse(
            _is_trusted_main_runner(
                Path("docker.yml"), "image_publish", {},
                valid_runner.replace("ng-main-run-{0}", "ng-main-run-123"),
            )
        )
        self.assertFalse(
            _is_trusted_main_runner(
                Path("docker.yml"), "image_publish", {},
                valid_runner.replace("refs/heads/main", "refs/heads/other"),
            )
        )

    def test_reusable_workflows_must_keep_runner_policy_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workflow_dir = Path(temporary_directory)
            (workflow_dir / "reusable.yml").write_text(
                yaml.safe_dump(
                    {"jobs": {"validate": {"uses": "org/repo/.github/workflows/ci.yml@main"}}},
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            violations = _runner_policy_violations(workflow_dir)

        self.assertEqual(len(violations), 1)
        self.assertIn("reusable workflow runner is not visible", violations[0])

    def test_workflow_without_runner_assignments_keeps_the_catch_all_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workflow_dir = Path(temporary_directory)
            (workflow_dir / "empty-jobs.yml").write_text(
                "jobs: {}\n",
                encoding="utf-8",
            )

            violations = _runner_policy_violations(workflow_dir)

        self.assertEqual(
            violations,
            ["no checked-in workflow runner assignments were found"],
        )

    def test_quoted_runner_key_in_yaml_file_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workflow_dir = Path(temporary_directory)
            (workflow_dir / "quoted-runner.yaml").write_text(
                "name: runner policy regression\n"
                "on: push\n"
                "jobs:\n"
                "  test:\n"
                "    \"runs-on\": self-hosted\n"
                "    steps: []\n",
                encoding="utf-8",
            )

            violations = _runner_policy_violations(workflow_dir)

        self.assertEqual(len(violations), 1)
        self.assertIn("unsupported runner assignment 'self-hosted'", violations[0])

    def test_matrix_include_cannot_add_a_persistent_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            workflow_dir = Path(temporary_directory)
            (workflow_dir / "matrix.yml").write_text(
                "jobs:\n"
                "  test:\n"
                "    runs-on: ${{ matrix.os }}\n"
                "    strategy:\n"
                "      matrix:\n"
                "        os: [ubuntu-latest]\n"
                "        include:\n"
                "          - os: self-hosted\n",
                encoding="utf-8",
            )

            violations = _runner_policy_violations(workflow_dir)

        self.assertEqual(len(violations), 1)
        self.assertIn("unsupported runner assignment '${{ matrix.os }}'", violations[0])


if __name__ == "__main__":
    unittest.main()

