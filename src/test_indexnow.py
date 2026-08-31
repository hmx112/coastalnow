import importlib.util
import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent))


class IndexNowIntegrationTests(unittest.TestCase):
    KEY = "d9841f79a4de725f16d6ed88c7807a68"
    BASE_URL = "https://coastalnowtides.com"

    def module(self):
        spec = importlib.util.find_spec("indexnow_submit")
        self.assertIsNotNone(spec, "src/indexnow_submit.py must exist")
        return __import__("indexnow_submit")

    def require_attr(self, module, name):
        self.assertTrue(hasattr(module, name), f"indexnow_submit.{name} must exist")
        return getattr(module, name)

    def test_public_html_paths_map_to_canonical_site_urls(self):
        module = self.module()
        self.assertEqual(module.public_path_to_url("public/index.html"), self.BASE_URL + "/")
        self.assertEqual(module.public_path_to_url("public/fishing/index.html"), self.BASE_URL + "/fishing/")
        self.assertEqual(
            module.public_path_to_url("public/tides/california/san-diego/fishing/index.html"),
            self.BASE_URL + "/tides/california/san-diego/fishing/",
        )
        self.assertIsNone(module.public_path_to_url("public/data/activities/san-diego.json"))
        self.assertIsNone(module.public_path_to_url("public/assets/activity.css"))
        self.assertIsNone(module.public_path_to_url("public/sitemap.xml"))
        self.assertIsNone(module.public_path_to_url("public/robots.txt"))

    def test_changed_page_urls_include_added_modified_and_deleted_html_only(self):
        module = self.module()
        diff = "\n".join([
            "M\tpublic/index.html",
            "M\tpublic/fishing/index.html",
            "A\tpublic/tides/california/san-diego/fishing/index.html",
            "D\tpublic/tides/florida/legacy/index.html",
            "M\tpublic/data/activities/san-diego.json",
            "M\tpublic/assets/activity.css",
        ])
        self.assertEqual(
            module.changed_page_urls(diff),
            [
                self.BASE_URL + "/",
                self.BASE_URL + "/fishing/",
                self.BASE_URL + "/tides/california/san-diego/fishing/",
                self.BASE_URL + "/tides/florida/legacy/",
            ],
        )

    def test_first_key_file_addition_bootstraps_from_sitemap(self):
        module = self.module()
        diff = f"A\tpublic/{self.KEY}.txt\nM\tpublic/index.html\n"
        sitemap = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
  <url><loc>https://coastalnowtides.com/</loc></url>
  <url><loc>https://coastalnowtides.com/fishing/</loc></url>
  <url><loc>https://coastalnowtides.com/tides/california/san-diego/</loc></url>
</urlset>"""
        self.assertTrue(module.is_bootstrap_diff(diff))
        self.assertEqual(
            module.select_submission_urls(diff, sitemap),
            [
                self.BASE_URL + "/",
                self.BASE_URL + "/fishing/",
                self.BASE_URL + "/tides/california/san-diego/",
            ],
        )

    def test_normal_push_submits_only_changed_pages_not_entire_sitemap(self):
        module = self.module()
        diff = "M\tpublic/fishing/index.html\nM\tpublic/data/activities/san-diego.json\n"
        sitemap = """<?xml version=\"1.0\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url><loc>https://coastalnowtides.com/</loc></url><url><loc>https://coastalnowtides.com/fishing/</loc></url></urlset>"""
        self.assertFalse(module.is_bootstrap_diff(diff))
        self.assertEqual(module.select_submission_urls(diff, sitemap), [self.BASE_URL + "/fishing/"])

    def test_payload_uses_official_bulk_indexnow_shape(self):
        module = self.module()
        urls = [self.BASE_URL + "/", self.BASE_URL + "/fishing/"]
        payload = module.build_payload(urls)
        self.assertEqual(payload["host"], "coastalnowtides.com")
        self.assertEqual(payload["key"], self.KEY)
        self.assertEqual(payload["keyLocation"], self.BASE_URL + f"/{self.KEY}.txt")
        self.assertEqual(payload["urlList"], urls)
        json.dumps(payload)

    def test_batches_never_exceed_indexnow_10000_url_limit(self):
        module = self.module()
        urls = [f"{self.BASE_URL}/page-{i}/" for i in range(10001)]
        batches = list(module.batch_urls(urls))
        self.assertEqual([len(batch) for batch in batches], [10000, 1])

    def test_success_status_accepts_initial_202_and_normal_200(self):
        module = self.module()
        self.assertTrue(module.is_success_status(200))
        self.assertTrue(module.is_success_status(202))
        self.assertFalse(module.is_success_status(400))
        self.assertFalse(module.is_success_status(403))
        self.assertFalse(module.is_success_status(429))

    def test_post_batch_sends_utf8_json_to_official_indexnow_endpoint(self):
        module = self.module()
        post_batch = self.require_attr(module, "post_batch")
        captured = {}

        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        def opener(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return Response()

        urls = [self.BASE_URL + "/fishing/"]
        status = post_batch(urls, opener=opener)
        request = captured["request"]
        self.assertEqual(status, 200)
        self.assertEqual(request.full_url, "https://api.indexnow.org/indexnow")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(json.loads(request.data.decode("utf-8")), module.build_payload(urls))
        self.assertGreater(captured["timeout"], 0)

    def test_submit_urls_retries_temporary_403_then_accepts_initial_202(self):
        module = self.module()
        submit_urls = self.require_attr(module, "submit_urls")
        attempts = []
        sleeps = []

        class Response:
            status = 202
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        def opener(request, timeout):
            attempts.append(request.full_url)
            if len(attempts) == 1:
                raise HTTPError(request.full_url, 403, "key not propagated yet", {}, None)
            return Response()

        statuses = submit_urls(
            [self.BASE_URL + "/"],
            opener=opener,
            sleep=lambda seconds: sleeps.append(seconds),
            max_attempts=3,
            retry_delay=0.01,
        )
        self.assertEqual(statuses, [202])
        self.assertEqual(len(attempts), 2)
        self.assertEqual(sleeps, [0.01])

    def test_run_submission_uses_git_diff_and_sitemap_then_submits(self):
        module = self.module()
        run_submission = self.require_attr(module, "run_submission")
        calls = {}
        diff = f"A\tpublic/{self.KEY}.txt\n"
        sitemap = """<?xml version=\"1.0\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url><loc>https://coastalnowtides.com/</loc></url><url><loc>https://coastalnowtides.com/fishing/</loc></url></urlset>"""

        def diff_loader(before, after):
            calls["diff"] = (before, after)
            return diff

        def sitemap_loader():
            calls["sitemap"] = True
            return sitemap

        def submitter(urls):
            calls["urls"] = list(urls)
            return [200]

        count = run_submission(
            "before-sha",
            "after-sha",
            diff_loader=diff_loader,
            sitemap_loader=sitemap_loader,
            submitter=submitter,
        )
        self.assertEqual(count, 2)
        self.assertEqual(calls["diff"], ("before-sha", "after-sha"))
        self.assertTrue(calls["sitemap"])
        self.assertEqual(calls["urls"], [self.BASE_URL + "/", self.BASE_URL + "/fishing/"])

    def test_main_push_workflow_is_isolated_from_content_refresh_workflows(self):
        workflow = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "indexnow.yml")
        self.assertTrue(workflow.exists(), "dedicated .github/workflows/indexnow.yml must exist")
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("branches:", text)
        self.assertIn("- main", text)
        self.assertIn('"public/**"', text)
        self.assertIn("fetch-depth: 2", text)
        self.assertIn("python src/indexnow_submit.py", text)
        self.assertIn("github.event.before", text)
        self.assertIn("github.sha", text)
        self.assertNotIn("contents: write", text)


if __name__ == "__main__":
    unittest.main()
