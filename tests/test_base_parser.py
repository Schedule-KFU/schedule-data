import unittest
import json
import tempfile
from pathlib import Path

from base_parser import preserve_lesson_ids, save_database_with_cache_check


class BaseParserTests(unittest.TestCase):
    def test_existing_ids_are_preserved_when_lessons_change(self):
        def lesson(identifier, subject):
            return {
                "id": identifier,
                "subject": subject,
                "timeStart": "08:30",
                "timeEnd": "10:00",
                "teacher": "Иванов И.И.",
                "room": "101"
            }

        def database(items):
            return {
                "groups": [
                    {
                        "group": "09-611",
                        "days": [{"dayIndex": 1, "lessons": items}]
                    }
                ]
            }

        old = database([lesson("09-611-1", "Math"), lesson("09-611-2", "Physics")])
        new = database([lesson("09-611-1", "NewSubject"), lesson("09-611-2", "Math"), lesson("09-611-3", "Physics")])
        preserve_lesson_ids(new, old)
        lessons = new["groups"][0]["days"][0]["lessons"]
        # Math and Physics should preserve 09-611-1 and 09-611-2
        self.assertEqual(lessons[1]["id"], "09-611-1")
        self.assertEqual(lessons[2]["id"], "09-611-2")
        # NewSubject should get a newly generated ID
        self.assertEqual(len({x["id"] for x in lessons}), 3)

    def test_save_rejects_large_data_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            output_file = Path(directory) / "test_schedule.json"
            old_db = {
                "groups": [
                    {"group": f"09-{i}", "days": [{"lessons": [{"id": f"09-{i}-1"}]}]}
                    for i in range(10)
                ]
            }
            output_file.write_text(json.dumps(old_db), encoding="utf-8")
            previous_bytes = output_file.read_bytes()

            # Attempt to overwrite with only 2 groups (<70% of 10)
            shrunk_db = {
                "groups": [
                    {"group": f"09-{i}", "days": [{"lessons": [{"id": f"09-{i}-1"}]}]}
                    for i in range(2)
                ]
            }
            with self.assertRaises(ValueError):
                save_database_with_cache_check(shrunk_db, str(output_file))

            # The original healthy file must be preserved
            self.assertEqual(output_file.read_bytes(), previous_bytes)

    def test_identical_content_preserves_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            output_file = Path(directory) / "test_schedule.json"
            db = {
                "groups": [{"group": "09-611", "days": [{"lessons": [{"id": "1", "timeStart": "08:30", "timeEnd": "10:00", "subject": "Math", "teacher": "", "room": ""}]}]}],
                "updatedAt": "2026-09-01T00:00:00Z"
            }
            save_database_with_cache_check(db, str(output_file))
            previous_bytes = output_file.read_bytes()

            # Run again with a newer updatedAt
            save_database_with_cache_check({**db, "updatedAt": "2026-09-02T00:00:00Z"}, str(output_file))
            self.assertEqual(output_file.read_bytes(), previous_bytes)
