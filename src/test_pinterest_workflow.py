import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class PinterestWorkflowTests(unittest.TestCase):
    def test_daily_workflow_refreshes_after_source_merges_without_self_trigger(self):
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "update-pinterest.yml"
        self.assertTrue(workflow.exists(), "daily Pinterest workflow must exist")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn('cron: "17 15 * * *"', text)
        self.assertIn("push:", text)
        self.assertIn("branches:", text)
        self.assertIn("- main", text)
        self.assertIn('"src/pinterest/**"', text)
        self.assertIn('"src/generate_pinterest.py"', text)
        self.assertIn('"src/data/pinterest.json"', text)
        self.assertIn('"requirements-pinterest.txt"', text)
        self.assertNotIn('"public/pinterest/**"', text)
        self.assertIn("group: coastalnow-site-writes", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn('python-version: "3.12"', text)
        self.assertIn("pip install -r requirements-pinterest.txt", text)
        self.assertIn("python src/generate_pinterest.py", text)
        self.assertIn("python src/test_pinterest_catalog_schedule.py", text)
        self.assertIn("python src/test_pinterest_identity_surfing.py", text)
        self.assertIn("python src/test_pinterest_rss.py", text)
        self.assertIn("python src/test_pinterest_render.py", text)
        self.assertIn("python src/test_pinterest_photo_template.py", text)
        self.assertIn("python src/test_pinterest_generation.py", text)
        self.assertIn("python src/test_pinterest_workflow.py", text)
        self.assertIn("git add public/pinterest", text)
        self.assertIn('git commit -m "Update Pinterest distribution assets"', text)
        self.assertIn("git fetch origin main", text)
        self.assertIn("git rebase origin/main", text)
        self.assertLess(text.index("git fetch origin main"), text.index("git push"))
        self.assertLess(text.index("git rebase origin/main"), text.index("git push"))


if __name__ == "__main__":
    unittest.main()
