from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"


class WorkflowRunnerPolicyTests(unittest.TestCase):
    def test_public_workflows_never_select_persistent_runners(self) -> None:
        workflow_files = sorted(WORKFLOW_DIR.glob("*.yml"))
        self.assertTrue(workflow_files, "workflow files must be present")

        runner_lines = [
            f"{workflow.name}: {line.strip()}"
            for workflow in workflow_files
            for line in workflow.read_text(encoding="utf-8").splitlines()
            if line.lstrip().startswith("runs-on:") and "self-hosted" in line
        ]

        self.assertEqual(
            runner_lines,
            [],
            "public validation must not select a persistent self-hosted runner",
        )


if __name__ == "__main__":
    unittest.main()
