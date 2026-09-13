import tempfile
import unittest
from datetime import date
from pathlib import Path

from tools.gsc_report import classify_url, compare_snapshots, parse_pages_csv


class GscReportTests(unittest.TestCase):
    def test_classify_url_distinguishes_state_location_activity_and_other(self):
        self.assertEqual(
            classify_url("https://coastalnowtides.com/tides/california/"),
            {"page_type": "state", "state_slug": "california", "location_slug": ""},
        )
        self.assertEqual(
            classify_url("https://coastalnowtides.com/tides/california/oceanside/"),
            {"page_type": "location", "state_slug": "california", "location_slug": "oceanside"},
        )
        self.assertEqual(
            classify_url("https://coastalnowtides.com/tides/california/oceanside/fishing/"),
            {"page_type": "activity", "state_slug": "california", "location_slug": "oceanside"},
        )
        self.assertEqual(
            classify_url("https://coastalnowtides.com/methodology/"),
            {"page_type": "other", "state_slug": "", "location_slug": ""},
        )

    def test_pages_csv_maps_location_urls_and_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "Pages.csv"
            csv_path.write_text(
                "Top pages,Clicks,Impressions,CTR,Position\n"
                "https://coastalnowtides.com/tides/california/oceanside/,1,15,6.67%,9.87\n",
                encoding="utf-8",
            )
            rows = parse_pages_csv(csv_path, date(2026, 9, 13))

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["snapshot_date"], "2026-09-13")
        self.assertEqual(row["page_type"], "location")
        self.assertEqual(row["state_slug"], "california")
        self.assertEqual(row["location_slug"], "oceanside")
        self.assertEqual(row["impressions"], 15)
        self.assertEqual(row["clicks"], 1)
        self.assertAlmostEqual(row["ctr"], 6.67)
        self.assertAlmostEqual(row["avg_position"], 9.87)
        self.assertEqual(row["indexed"], "")
        self.assertEqual(row["first_impression_date"], "2026-09-13")

    def test_pages_csv_accepts_korean_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "Pages.csv"
            csv_path.write_text(
                "페이지,클릭수,노출수,CTR,평균 게재순위\n"
                "https://coastalnowtides.com/tides/florida/miami-beach/,0,8,0%,4.62\n",
                encoding="utf-8-sig",
            )
            rows = parse_pages_csv(csv_path, date(2026, 9, 13))
        self.assertEqual(rows[0]["location_slug"], "miami-beach")
        self.assertEqual(rows[0]["impressions"], 8)
        self.assertAlmostEqual(rows[0]["avg_position"], 4.62)

    def test_compare_reports_page_growth_position_improvement_and_state_totals(self):
        url = "https://coastalnowtides.com/tides/california/oceanside/"
        previous = [
            {
                "snapshot_date": "2026-09-06",
                "url": url,
                "page_type": "location",
                "state_slug": "california",
                "location_slug": "oceanside",
                "impressions": 10,
                "clicks": 0,
                "ctr": 0.0,
                "avg_position": 11.87,
                "indexed": "",
                "first_impression_date": "2026-09-06",
            }
        ]
        current = [
            {
                "snapshot_date": "2026-09-13",
                "url": url,
                "page_type": "location",
                "state_slug": "california",
                "location_slug": "oceanside",
                "impressions": 15,
                "clicks": 1,
                "ctr": 6.67,
                "avg_position": 9.87,
                "indexed": "",
                "first_impression_date": "2026-09-13",
            },
            {
                "snapshot_date": "2026-09-13",
                "url": "https://coastalnowtides.com/tides/florida/miami-beach/",
                "page_type": "location",
                "state_slug": "florida",
                "location_slug": "miami-beach",
                "impressions": 8,
                "clicks": 0,
                "ctr": 0.0,
                "avg_position": 4.62,
                "indexed": "",
                "first_impression_date": "2026-09-13",
            },
        ]

        report = compare_snapshots(previous, current)
        oceanside = report["pages"][url]
        self.assertEqual(oceanside["impressions_delta"], 5)
        self.assertEqual(oceanside["clicks_delta"], 1)
        self.assertAlmostEqual(oceanside["ctr_delta"], 6.67)
        self.assertAlmostEqual(oceanside["position_delta"], -2.0)
        self.assertEqual(oceanside["first_impression_date"], "2026-09-06")
        self.assertIn("https://coastalnowtides.com/tides/florida/miami-beach/", report["new_first_impressions"])
        self.assertEqual(report["states"]["california"]["current_impressions"], 15)
        self.assertEqual(report["states"]["california"]["impressions_delta"], 5)
        self.assertEqual(report["states"]["florida"]["impressions_delta"], 8)
        self.assertEqual(report["fastest_growing_states"][0]["state_slug"], "florida")


if __name__ == "__main__":
    unittest.main()
