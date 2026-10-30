import unittest
import json
import tempfile
from pathlib import Path

from parser_ifmib import (
    split_ifmib_cell_into_lessons,
    parse_ifmib_lesson_item,
    preserve_ifmib_lesson_ids,
    save_ifmib_database
)


class IFMiBCellTests(unittest.TestCase):
    def test_split_cell_with_slash_between_subjects(self):
        raw = 'Анатомия человека (лекция 2 нед.) Заикина Э.И./Биология (лекция 4-10 нед. ) Заботин Я.И. ауд.208 К.Маркса, 76 (кор.2)'
        parts = split_ifmib_cell_into_lessons(raw)
        self.assertEqual(len(parts), 2)
        p1 = parse_ifmib_lesson_item(parts[0])
        p2 = parse_ifmib_lesson_item(parts[1])
        self.assertEqual(p1['subject'], 'Анатомия человека')
        self.assertEqual(p1['teacher'], 'Заикина Э.И.')
        self.assertEqual(p1['building'], 'К.Маркса 76 корп. 2')
        self.assertEqual(p1['room'], '208')
        self.assertEqual(p2['subject'], 'Биология')
        self.assertEqual(p2['teacher'], 'Заботин Я.И.')
        self.assertEqual(p2['building'], 'К.Маркса 76 корп. 2')
        self.assertEqual(p2['room'], '208')

    def test_custom_time_parsing(self):
        raw = '10.30-12.55 Биология Галанин И.Ф.  ауд.207 Кремлевская, 18'
        lesson = parse_ifmib_lesson_item(raw)
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson['customTime']['start'], '10:30')
        self.assertEqual(lesson['customTime']['end'], '12:55')
        self.assertEqual(lesson['subject'], 'Биология')
        self.assertEqual(lesson['teacher'], 'Галанин И.Ф.')
        self.assertEqual(lesson['room'], '207')
        self.assertEqual(lesson['building'], 'Кремл. 18')

    def test_discontinuous_weeks_extraction(self):
        raw = 'Неорганическая и физколлоидная химия (8 лекций 4, 6, 8, 10, 12-13, 14, 16 нед.) Журавлева Ю.И. ауд. 204А К.Маркса, 74'
        lesson = parse_ifmib_lesson_item(raw)
        self.assertIsNotNone(lesson)
        self.assertEqual(lesson['type'], 'lecture')
        self.assertEqual(lesson['weekStart'], 4)
        self.assertEqual(lesson['weekEnd'], 16)
        self.assertEqual(lesson['weeks'], [4, 6, 8, 10, 12, 13, 14, 16])
        self.assertEqual(lesson['teacher'], 'Журавлева Ю.И.')
        self.assertEqual(lesson['room'], '204А')
        self.assertEqual(lesson['building'], 'К.Маркса 74')

    def test_clinical_facilities_and_hospitals(self):
        raw_gb7 = '10.00-11.30 Лучевая диагностика (1-15 нед.)  Минимуллин Н.А. учеб.ком. ГБ № 7'
        l_gb7 = parse_ifmib_lesson_item(raw_gb7)
        self.assertEqual(l_gb7['building'], 'ГБ № 7')
        self.assertEqual(l_gb7['room'], 'учеб. комната')
        self.assertEqual(l_gb7['subject'], 'Лучевая диагностика')

        raw_zdorovie = 'Общая хирургия (2-13 нед.)  Нуриев И.С., Демьянов С.Л.  учеб.ком. Здоровье семьи, 2-я Юго-Западная, 35'
        l_zdorovie = parse_ifmib_lesson_item(raw_zdorovie)
        self.assertEqual(l_zdorovie['building'], 'Здоровье семьи (2-я Юго-Западная 35)')
        self.assertEqual(l_zdorovie['room'], 'учеб. комната')
        self.assertEqual(l_zdorovie['subject'], 'Общая хирургия')

        raw_rkod = 'Патологическая анатомия Яхина А.Р.  учеб.ком. 3 РКОД Сибирский тракт, 31'
        l_rkod = parse_ifmib_lesson_item(raw_rkod)
        self.assertEqual(l_rkod['building'], 'РКОД (Сибирский тракт 31)')
        self.assertEqual(l_rkod['room'], 'учеб. комната 3')
        self.assertEqual(l_rkod['subject'], 'Патологическая анатомия')

    def test_id_preservation(self):
        def make_lesson(identifier, subject):
            return {
                "id": identifier, "subject": subject,
                "timeStart": "08:30", "timeEnd": "10:00",
                "teacher": "Иванов И.И.", "room": "204А"
            }
        old_db = {"groups": [{"id": "01.2-611 (а)", "group": "01.2-611 (а)", "days": [{"dayIndex": 1, "lessons": [make_lesson("id-1", "Биология"), make_lesson("id-2", "Химия")]}]}]}
        new_db = {"groups": [{"id": "01.2-611 (а)", "group": "01.2-611 (а)", "days": [{"dayIndex": 1, "lessons": [make_lesson("id-x", "Физика"), make_lesson("id-x", "Биология"), make_lesson("id-x", "Химия")]}]}]}

        preserve_ifmib_lesson_ids(new_db, old_db)
        lessons = new_db["groups"][0]["days"][0]["lessons"]
        self.assertEqual(lessons[1]["id"], "id-1")
        self.assertEqual(lessons[2]["id"], "id-2")
        self.assertEqual(len({l["id"] for l in lessons}), 3)

    def test_save_gate_rejects_empty_or_drastic_loss(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "schedule.json"
            old_db = {"groups": [{"group": f"01.2-60{i}", "days": [{"lessons": [{"id": f"{i}"}]}]} for i in range(10)]}
            path.write_text(json.dumps(old_db), encoding="utf-8")
            prev_content = path.read_bytes()

            with self.assertRaises(ValueError):
                save_ifmib_database({"groups": old_db["groups"][:2]}, path)
            self.assertEqual(path.read_bytes(), prev_content)


if __name__ == "__main__":
    unittest.main()
