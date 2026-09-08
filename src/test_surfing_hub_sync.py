import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "update-activities.yml",
    ROOT / ".github" / "workflows" / "update-activity-alerts.yml",
    ROOT / ".github" / "workflows" / "update-san-diego.yml",
)


class SurfingHubSyncTests(unittest.TestCase):
    def test_every_site_writer_stages_surfing_hub_output(self):
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                text = workflow.read_text(encoding="utf-8")
                self.assertIn(
                    "public/surfing",
                    text,
                    f"{workflow.name} rebuilds the Surfing hub but does not stage public/surfing",
                )


if __name__ == "__main__":
    unittest.main()
