"""Tests: diagnostics never disclose row values or API keys."""
import unittest
from schema_probe import describe


class TestSchemaProbe(unittest.TestCase):
    def test_only_keys_are_printed(self):
        raw = {"header": {"resultCode": "00"}, "body": {
            "items": {"item": [{"predcDt": "SENSITIVE-TIME", "actualHeight": "SECRET-HEIGHT",
                                "extrSe": 1}]}}}
        text = describe("high_low", raw)
        self.assertIn("actualHeight", text)
        self.assertIn("predcTdlvVl: MISSING", text)
        self.assertNotIn("SENSITIVE-TIME", text)
        self.assertNotIn("SECRET-HEIGHT", text)

    def test_series_is_inspected_independently(self):
        raw = {"response": {"header": {"resultCode": "00"}, "body": {
            "items": {"item": [{"predcDt": "SENSITIVE-TIME", "observedLevel": 55}]}}}}
        text = describe("series", raw)
        self.assertIn("observedLevel", text)
        self.assertNotIn("55", text)


if __name__ == "__main__":
    unittest.main()
