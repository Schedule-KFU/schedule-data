# Schedule KFU Data Provider

Automated schedule provider and parser for the Institute of Computational Mathematics and Information Technologies (IVMIIT) at Kazan Federal University (KFU).

## API Endpoints

- **Full Schedule (GitHub Pages):**
  `https://schedule-kfu.github.io/schedule-data/schedule.json`

- **Raw GitHub Endpoint:**
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/schedule.json`

## Automated Updates

The schedule is automatically updated every 4 hours directly from `kpfu.ru` via GitHub Actions.

## Data Structure (API Reference)

This section describes the structure of `schedule.json` for frontend and mobile app developers. The file provides a highly normalized and cleaned representation of the KFU schedule.

### Root Object
```json
{
  "version": 4,
  "semester": "1 семестр 2026/2027",
  "updatedAt": "2026-09-08T18:42:00Z",
  "sourceUrl": "https://kpfu.ru/portal/docs/.../Raspisanie.xlsx",
  "groups": [ ... ]
}
```
- `version`: Integer version of the JSON schema.
- `semester`: Human-readable current semester string.
- `updatedAt`: ISO 8601 timestamp of the last successful parse.
- `sourceUrl`: URL of the original `.xlsx` file used for generation.
- `groups`: Array of `Group` objects.

### Group Object
```json
{
  "id": "09-642 (1)",
  "group": "09-642 (1)",
  "course": "1 курс",
  "major": "ИНФОРМАЦИОННАЯ БЕЗОПАСНОСТЬ (10.03.01)",
  "shortGroup": "09-642 (1)",
  "specialization": "",
  "days": [ ... ]
}
```
- `id` / `group`: Unique identifier and name of the group.
- `course`: Course year (e.g., "1 курс", "1 курс (магистратура)").
- `major`: Full string of the major or field of study.
- `shortGroup` / `specialization`: Splitted identifiers (used internally for specific sub-faculties).
- `days`: Array of `Day` objects.

### Day Object
```json
{
  "dayName": "понедельник",
  "dayIndex": 1,
  "lessons": [ ... ]
}
```
- `dayName`: Lowercase Russian name of the day (`понедельник`, `вторник`, и т.д.).
- `dayIndex`: Integer representing the day of the week (1 = Monday, 6 = Saturday).
- `lessons`: Array of `Lesson` objects scheduled for this day.

### Lesson Object (Core Domain)
This is the most detailed entity. 
**Important for UI:** Multiple `Lesson` objects can have the exact same `time` and `subject`. This represents parallel subgroups (e.g., one teacher takes half the group in room 403, another teacher takes the other half in room 407). The app UI should group such lessons into a single time-slot card. **Do NOT use a horizontal carousel or swipeable views for this.** Instead, render them as a vertical list of rows (one row per teacher/room) inside the same card, so the user can see all subgroups at a glance.

```json
{
  "id": "09-642 (1)-685",
  "subject": "Физика",
  "rawText": "Физика. Соловьев О.В. Клековкина В.В., ауд. 706,707(Кремл. 16А)",
  "teacher": "Соловьев О.В.",
  "room": "706",
  "building": "Кремл. 16А",
  "type": "other",
  "isAdditional": false,
  "weekType": "first_half",
  "weekStart": 1,
  "weekEnd": 9,
  "time": "08:30-10:00",
  "timeStart": "08:30",
  "timeEnd": "10:00"
}
```

#### Fields Breakdown:
- **`id`**: Unique string ID for the lesson (format: `<group_id>-<increment>`).
- **`subject`**: Cleaned name of the discipline without teachers, rooms, or week numbers.
- **`rawText`**: The original unparsed chunk of text from the Excel cell. Useful for debugging or showing as a fallback tooltip.
- **`teacher`**: Name of the teacher(s). If multiple teachers teach the *same* subgroup together, they are separated by a comma (e.g. `Соловьев О.В., Клековкина В.В.`).
- **`room`**: Room number. If a subgroup spans multiple rooms, they are separated by commas (e.g., `706,707`).
- **`building`**: The building name (e.g., `Кремл. 35`, `УНИКС`).
- **`type`**: Type of the lesson. Enum:
  - `"lecture"`: Лекция
  - `"practice"`: Практическое занятие
  - `"lab"`: Лабораторная работа
  - `"distance"`: Дистанционное занятие
  - `"eor"`: ЭОР (Электронный образовательный ресурс)
  - `"other"`: Другое (тип не указан явно)
- **`isAdditional`**: Boolean. `true` if the lesson is marked as "дополнительная пара" (suffix `- д.`). The UI might want to highlight these differently.
- **`weekType`**: Describes the parity/recurrence of the lesson. Enum:
  - `"all"`: Every week
  - `"odd"`: Odd weeks only (нечетные, н/н)
  - `"even"`: Even weeks only (четные, ч/н)
  - `"first_half"`: First half of the semester (weeks 1-9)
  - `"second_half"`: Second half of the semester (weeks 10-18)
- **`weekStart` / `weekEnd`**: Integer bounds for the weeks this lesson is active. Usually `1` and `18`.
- **`time` / `timeStart` / `timeEnd`**: String representations of the lesson's time schedule. Automatically overrides standard university time-slots if a custom time is specified in the Excel file (e.g., for sports in UNICS).
