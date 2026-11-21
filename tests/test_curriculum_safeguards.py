import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
import base_curriculum_parser as crawler


class CurriculumSafeguardTests(unittest.TestCase):
    def test_http_error_is_retried_and_reported(self):
        response = requests.Response()
        response.status_code = 503
        response.url = "https://example.invalid/plan"
        response._content = b"unavailable"
        with patch.object(crawler.requests, "get", return_value=response) as get, patch.object(crawler.time, "sleep"):
            with self.assertRaises(ConnectionError):
                crawler.fetch_url(response.url)
        self.assertEqual(get.call_count, 3)

    def test_one_unreadable_plan_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "curriculum.json"
            output.write_text(json.dumps({"plans": [{"id": "old"}]}), encoding="utf-8")
            previous = output.read_bytes()
            speciality = {"id": "1", "code": "01.03.01", "name": "Math", "degree": "bachelor"}
            plan = {"id": "42", "name": "Plan", "profile": "", "year": 2026, "form": "full"}
            other_plan = {**plan, "id": "43"}
            with patch.object(crawler, "__file__", str(root / "parser.py")), \
                 patch.object(crawler, "parse_specialities", return_value=[speciality]), \
                 patch.object(crawler, "parse_plans_for_speciality", return_value=[plan, other_plan]), \
                 patch.object(crawler, "parse_study_plan_tables", side_effect=[[{"isBlock": False, "semesters": []}], []]), \
                 patch.object(crawler.time, "sleep"):
                with self.assertRaises(ValueError):
                    crawler.run_curriculum_crawler(1, "Faculty", "curriculum.json")
            self.assertEqual(output.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
