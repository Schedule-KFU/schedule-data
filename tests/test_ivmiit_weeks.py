import unittest
from parser import extract_explicit_weeks, parse_lesson_text

class IvmiitWeeksTests(unittest.TestCase):
    def test_composite_week_ranges(self):
        text = '(1-9, 11-18 нед.) Иностранный язык. Еремеева Г.Р. ауд. 312 (Кремл. 35)'
        weeks = extract_explicit_weeks(text)
        self.assertIsNotNone(weeks)
        self.assertIn(9, weeks)
        self.assertNotIn(10, weeks)
        self.assertIn(11, weeks)

    def test_discontinuous_weeks(self):
        text = '(1-8 нед., 16-18 нед.) Иностранный язык'
        weeks = extract_explicit_weeks(text)
        self.assertEqual(weeks, [1, 2, 3, 4, 5, 6, 7, 8, 16, 17, 18])

    def test_continuous_weeks_return_none(self):
        text = '(1-18 нед.) Информатика'
        self.assertIsNone(extract_explicit_weeks(text))

    def test_discrete_weeks(self):
        text = '(5, 7 нед.) Физика'
        self.assertEqual(extract_explicit_weeks(text), [5, 7])

    def test_parsed_lesson_contains_weeks(self):
        text = '(1-9, 11-18 нед.) Иностранный язык. Еремеева Г.Р. ауд. 312 (Кремл. 35)'
        res = parse_lesson_text(text)
        self.assertTrue(len(res) > 0)
        self.assertEqual(res[0]['weeks'], [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18])

if __name__ == '__main__':
    unittest.main()
