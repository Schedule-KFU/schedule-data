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

    def test_multi_teacher_alternating_weeks_split(self):
        raw = ('Статистические методы анализа в биологии и медицине (6 лекций 2, 4, 6, 8, 12, 14 нед.) Бурыкин И.М. ауд. 204А К.Маркса, 74 /'
               'Гигиена (7 лекций) 3, 7, 11, 15 нед. Валеева Э.Р.,  5, 9, 13 нед. Степанова Н.В.  ауд.204А К.Маркса, 74')
        parts = split_ifmib_cell_into_lessons(raw)
        self.assertEqual(len(parts), 3)

        p1 = parse_ifmib_lesson_item(parts[0])
        self.assertEqual(p1['subject'], 'Статистические методы анализа в биологии и медицине')
        self.assertEqual(p1['teacher'], 'Бурыкин И.М.')
        self.assertEqual(p1['type'], 'lecture')
        self.assertEqual(p1['weekType'], 'even')
        self.assertEqual(p1['weeks'], [2, 4, 6, 8, 12, 14])
        self.assertEqual(p1['room'], '204А')
        self.assertEqual(p1['building'], 'К.Маркса 74')

        p2 = parse_ifmib_lesson_item(parts[1])
        self.assertEqual(p2['subject'], 'Гигиена')
        self.assertEqual(p2['teacher'], 'Валеева Э.Р.')
        self.assertEqual(p2['type'], 'lecture')
        self.assertEqual(p2['weekType'], 'odd')
        self.assertEqual(p2['weeks'], [3, 7, 11, 15])
        self.assertEqual(p2['room'], '204А')
        self.assertEqual(p2['building'], 'К.Маркса 74')

        p3 = parse_ifmib_lesson_item(parts[2])
        self.assertEqual(p3['subject'], 'Гигиена')
        self.assertEqual(p3['teacher'], 'Степанова Н.В.')
        self.assertEqual(p3['type'], 'lecture')
        self.assertEqual(p3['weekType'], 'odd')
        self.assertEqual(p3['weeks'], [5, 9, 13])
        self.assertEqual(p3['room'], '204А')
        self.assertEqual(p3['building'], 'К.Маркса 74')

    def test_missing_closing_paren_lecture_count(self):
        raw = 'Общественное здоровье и здравоохранение (7 лекций  3, 7, 11, 15 нед. Степанова Н.В., 5, 9, 13 нед.  Валеева Э.Р. ауд. 205А К.Маркса, 74'
        parts = split_ifmib_cell_into_lessons(raw)
        self.assertEqual(len(parts), 2)

        p1 = parse_ifmib_lesson_item(parts[0])
        self.assertEqual(p1['subject'], 'Общественное здоровье и здравоохранение')
        self.assertEqual(p1['teacher'], 'Степанова Н.В.')
        self.assertEqual(p1['type'], 'lecture')
        self.assertEqual(p1['weekType'], 'odd')
        self.assertEqual(p1['weeks'], [3, 7, 11, 15])
        self.assertEqual(p1['room'], '205А')
        self.assertEqual(p1['building'], 'К.Маркса 74')

        p2 = parse_ifmib_lesson_item(parts[1])
        self.assertEqual(p2['subject'], 'Общественное здоровье и здравоохранение')
        self.assertEqual(p2['teacher'], 'Валеева Э.Р.')
        self.assertEqual(p2['type'], 'lecture')
        self.assertEqual(p2['weekType'], 'odd')
        self.assertEqual(p2['weeks'], [5, 9, 13])
        self.assertEqual(p2['room'], '205А')
        self.assertEqual(p2['building'], 'К.Маркса 74')

    def test_multi_teacher_distinct_classrooms(self):
        raw = ('Методы исследования в бологии и медицине (3-4 нед. Харитонова М.А. ауд.016в  Кремл.18, '
               '5-6 нед. Сыромятникова В.Ю. ауд.203В Кремл.18, 7-8 нед. Шайдуллова К.С.  Ауд.212 (бокс) КМ, 76 (к.2), '
               '9-12 нед. Саляхутдинова Ш.М. ауд. 301 КМ, 74, 13-15 нед. Ибрагимова М.Я. Ауд.113В  Кремл. 18')
        parts = split_ifmib_cell_into_lessons(raw)
        self.assertEqual(len(parts), 5)

        p1 = parse_ifmib_lesson_item(parts[0])
        self.assertEqual(p1['teacher'], 'Харитонова М.А.')
        self.assertEqual(p1['weekStart'], 3)
        self.assertEqual(p1['weekEnd'], 4)
        self.assertEqual(p1['room'], '016в')
        self.assertEqual(p1['building'], 'Кремл. 18')

        p3 = parse_ifmib_lesson_item(parts[2])
        self.assertEqual(p3['teacher'], 'Шайдуллова К.С.')
        self.assertEqual(p3['weekStart'], 7)
        self.assertEqual(p3['weekEnd'], 8)
        self.assertEqual(p3['room'], '212')
        self.assertEqual(p3['building'], 'К.Маркса 76 корп. 2')

        p4 = parse_ifmib_lesson_item(parts[3])
        self.assertEqual(p4['teacher'], 'Саляхутдинова Ш.М.')
        self.assertEqual(p4['weekStart'], 9)
        self.assertEqual(p4['weekEnd'], 12)
        self.assertEqual(p4['room'], '301')
        self.assertEqual(p4['building'], 'К.Маркса 74')


if __name__ == "__main__":
    unittest.main()
