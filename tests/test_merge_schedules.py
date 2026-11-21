import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import merge_schedules


class MergeSchedulesTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / "schedule_combined.json"
        self.module_path = patch.object(merge_schedules, "__file__", str(self.root / "merge_schedules.py"))
        self.module_path.start()
        self.addCleanup(self.module_path.stop)

    def write_source(self, name, group):
        data = {"semester": "1 semester", "groups": [{"group": group, "days": [{"lessons": [{"id": group}]}]}]}
        (self.root / name).write_text(json.dumps(data), encoding="utf-8")

    def test_missing_institute_keeps_existing_file(self):
        self.write_source("schedule.json", "09-1")
        self.write_source("schedule_physics.json", "06-1")
        self.output.write_text("previous", encoding="utf-8")
        with self.assertRaises((ValueError, OSError)):
            merge_schedules.merge_schedules()
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous")

    def test_empty_institute_keeps_existing_file(self):
        self.write_source("schedule.json", "09-1")
        self.write_source("schedule_physics.json", "06-1")
        (self.root / "schedule_ifmib.json").write_text('{"groups": []}', encoding="utf-8")
        self.output.write_text("previous", encoding="utf-8")
        with self.assertRaises(ValueError):
            merge_schedules.merge_schedules()
        self.assertEqual(self.output.read_text(encoding="utf-8"), "previous")

    def test_identical_merge_is_byte_identical(self):
        for name, group in (("schedule.json", "09-1"), ("schedule_physics.json", "06-1"), ("schedule_ifmib.json", "01-1")):
            self.write_source(name, group)
        merge_schedules.merge_schedules()
        previous = self.output.read_bytes()
        merge_schedules.merge_schedules()
        self.assertEqual(self.output.read_bytes(), previous)

    def test_large_drop_in_combined_output_is_rejected(self):
        for name, group in (("schedule.json", "09-1"), ("schedule_physics.json", "06-1"), ("schedule_ifmib.json", "01-1")):
            self.write_source(name, group)
        old = {"groups": [{"group": str(i), "days": [{"lessons": [{"id": str(i)}]}]} for i in range(10)]}
        self.output.write_text(json.dumps(old), encoding="utf-8")
        previous = self.output.read_bytes()
        with self.assertRaises(ValueError):
            merge_schedules.merge_schedules()
        self.assertEqual(self.output.read_bytes(), previous)

    def test_mismatched_semesters_are_rejected(self):
        for name, group in (("schedule.json", "09-1"), ("schedule_physics.json", "06-1"), ("schedule_ifmib.json", "01-1")):
            self.write_source(name, group)
        source = self.root / "schedule_ifmib.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        data["semester"] = "2 semester"
        source.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ValueError):
            merge_schedules.merge_schedules()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
