import unittest

from seo import activity_robots_directive


class StableActivityIndexingTests(unittest.TestCase):
    def test_missing_activity_result_remains_noindex(self):
        self.assertEqual(activity_robots_directive(None), "noindex,follow")
        self.assertEqual(activity_robots_directive({}), "noindex,follow")

    def test_generated_limited_activity_page_stays_indexable(self):
        result = {
            "today": {"status": "Limited", "confidence": "Limited"},
            "tomorrow": {"status": "Limited", "confidence": "Limited"},
        }
        self.assertEqual(activity_robots_directive(result), "index,follow")

    def test_generated_unavailable_day_does_not_toggle_index_state(self):
        result = {
            "today": {"status": "Unavailable", "confidence": "Unavailable"},
            "tomorrow": {"status": "Limited", "confidence": "Limited"},
        }
        self.assertEqual(activity_robots_directive(result), "index,follow")


if __name__ == "__main__":
    unittest.main()
