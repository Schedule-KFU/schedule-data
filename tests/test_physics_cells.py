import unittest
import json
import tempfile
from pathlib import Path

from parser_physics import extract_weeks, extract_explicit_weeks, parse_physics_cell, save_physics_database, preserve_physics_lesson_ids


class PhysicsCellTests(unittest.TestCase):
    def test_subject_with_capitalized_second_word_is_not_mistaken_for_teacher(self):
        lessons = parse_physics_cell("История России (пр)\nИбрагимов Р.Р.\n5-15н, 809")
        self.assertEqual(lessons[0]["subject"], "История России")
        self.assertEqual(lessons[0]["teacher"], "Ибрагимов Р.Р.")

    def test_discontinuous_week_list_is_parsed_without_room_numbers(self):
        self.assertEqual(extract_explicit_weeks("Поминов А.И.\n1,2,6-16н, 2 конференц-зал"), [1, 2, *range(6, 17)])
        self.assertEqual(extract_explicit_weeks("2, 4-14н, 117"), [2, *range(4, 15)])
        self.assertIsNone(extract_explicit_weeks("1-18н, 806"))
        self.assertIsNone(extract_explicit_weeks("ауд. 117"))
        self.assertEqual(extract_weeks("1-9, 11-18н, 905"), (1, 18, "all"))
        self.assertEqual(extract_weeks("1-2, 4-5, 7-8, 10-12, 14-18н, 905"), (1, 18, "all"))

    def test_discontinuous_weeks_are_kept_in_parsed_lesson(self):
        lessons = parse_physics_cell("Основы лидерства (пр)\nПоминов А.И.\n1,2,6-16н, 2 конференц-зал")
        self.assertEqual(lessons[0]["weeks"], [1, 2, *range(6, 17)])
    def test_existing_ids_are_preserved_when_a_lesson_is_inserted(self):
        def lesson(identifier, subject):
            return {"id": identifier, "subject": subject, "timeStart": "10:10", "timeEnd": "11:40", "teacher": "", "room": ""}
        def database(items):
            return {"groups": [{"group": "06-321", "days": [{"dayIndex": 2, "lessons": items}]}]}
        old = database([lesson("06-321-1", "A"), lesson("06-321-2", "B")])
        new = database([lesson("06-321-1", "New"), lesson("06-321-2", "A"), lesson("06-321-3", "B")])
        preserve_physics_lesson_ids(new, old)
        lessons = new["groups"][0]["days"][0]["lessons"]
        self.assertEqual([x["id"] for x in lessons[1:]], ["06-321-1", "06-321-2"])
        self.assertEqual(len({x["id"] for x in lessons}), 3)
    def test_regular_classes_are_not_dropped_due_to_teacher_surname(self):
        lessons = parse_physics_cell("Математический анализ (л)\nТурилова Е.А.\n1-18н, 806")
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["subject"], "Математический анализ")
        self.assertEqual(lessons[0]["teacher"], "Турилова Е.А.")
    def test_save_rejects_large_data_loss_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schedule.json"
            old = {"groups": [{"group": str(i), "days": [{"lessons": [{"id": str(i)}]}]} for i in range(10)]}
            path.write_text(json.dumps(old), encoding="utf-8")
            previous = path.read_bytes()
            with self.assertRaises(ValueError):
                save_physics_database({"groups": old["groups"][:2]}, path)
            self.assertEqual(path.read_bytes(), previous)

    def test_identical_content_preserves_timestamp_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "schedule.json"
            db = {"groups": [{"group": "06-321", "days": [{"lessons": [{"id": "1"}]}]}], "updatedAt": "first"}
            save_physics_database(db, path)
            previous = path.read_bytes()
            save_physics_database({**db, "updatedAt": "second"}, path)
            self.assertEqual(path.read_bytes(), previous)

    def test_inline_building_does_not_hide_second_subject(self):
        raw = (
            "Статистическая радиофизика (лаб) Коротышкин Д.В.\n"
            "1-17н, 1/2гр. ч.н, 1/2гр. н.н, 1203 "
            "Электродинамика сверхвысоких частот (лаб) Дуглав А.В. "
            "1-18н, 1/2гр. ч.н, 1/2гр. н.н, 251 гл.зд."
        )
        lessons = parse_physics_cell(raw)
        self.assertEqual([item["subject"] for item in lessons], [
            "Статистическая радиофизика", "Электродинамика сверхвысоких частот"
        ])

    def test_both_subgroup_parities_mean_the_class_exists_every_week(self):
        self.assertEqual(extract_weeks("1-17н, 1/2гр. ч.н, 1/2гр. н.н, 1203"), (1, 17, "all"))
        self.assertEqual(extract_weeks("1-17н, ч.н, 1203"), (1, 17, "even"))
        self.assertEqual(extract_weeks("1-17н, н.н, 1203"), (1, 17, "odd"))
        self.assertEqual(extract_weeks("6-16 н., ч\\н Шиманская Н.Н., ауд. 1а"), (6, 16, "even"))


if __name__ == "__main__":
    unittest.main()
