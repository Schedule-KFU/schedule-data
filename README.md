# Schedule KFU Data Provider

Automated schedule provider and curriculum parser for:
- **Institute of Computational Mathematics and Information Technologies (IVMIIT)**
- **Institute of Physics**
at Kazan Federal University (KFU).

## API Endpoints

### 📅 Schedule Endpoints

#### IVMIIT (Institute of Computational Mathematics and Information Technologies):
- **Full Schedule (GitHub Pages):**  
  `https://schedule-kfu.github.io/schedule-data/schedule.json`
- **Raw GitHub Endpoint:**  
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/schedule.json`

#### Institute of Physics:
- **Full Schedule (GitHub Pages):**  
  `https://schedule-kfu.github.io/schedule-data/schedule_physics.json`
- **Raw GitHub Endpoint:**  
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/schedule_physics.json`

### 📚 Curriculum Endpoints (Study Plans)

#### IVMIIT:
- **Full Curriculum (GitHub Pages):**  
  `https://schedule-kfu.github.io/schedule-data/curriculum_ivmiit.json`
- **Raw GitHub Endpoint:**  
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/curriculum_ivmiit.json`

#### Institute of Physics:
- **Full Curriculum (GitHub Pages):**  
  `https://schedule-kfu.github.io/schedule-data/curriculum_physics.json`
- **Raw GitHub Endpoint:**  
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/curriculum_physics.json`

## Automated Updates

The schedule and curriculum plans are automatically updated twice daily (06:00 and 22:00 MSK / UTC+3) directly from `kpfu.ru` via GitHub Actions.

---

## Schedule Data Structure (API Reference)

This section describes the structure of `schedule.json` and `schedule_physics.json` for frontend and mobile app developers. The files provide a normalized, cleaned representation of the KFU schedule.

> [!NOTE]
> **Institute Differences:**
> - **IVMIIT:** Group identifiers follow the `09-xxx` format (e.g. `09-441`, `09-122`). Primary building: `Кремл. 35` (Second High-Rise Building).
> - **Institute of Physics:** Group identifiers follow the `06-xxx` format (e.g. `06-401`, `06-601`, `06-502`). Primary building: `Кремл. 16А` (Physics Building). Teacher-training tracks also attend classes at `Межлаука 1`, and astronomy sessions take place at `Астрономическая 18` (Observatory).

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
- `version`: Integer schema version.
- `semester`: Human-readable current semester label.
- `updatedAt`: ISO 8601 timestamp of the last successful parse.
- `sourceUrl`: URL of the source `.xlsx` spreadsheet.
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
- `id` / `group`: Unique identifier and display name of the group.
- `course`: Academic year / level (e.g. `"1 курс"`, `"1 курс (магистратура)"`).
- `major`: Field of study / major description.
- `shortGroup` / `specialization`: Normalized split identifiers.
- `days`: Array of `Day` objects.

### Day Object
```json
{
  "dayName": "понедельник",
  "dayIndex": 1,
  "lessons": [ ... ]
}
```
- `dayName`: Lowercase Russian weekday name (`понедельник`, `вторник`, etc.).
- `dayIndex`: Integer representing day of the week (1 = Monday, 6 = Saturday).
- `lessons`: Array of `Lesson` objects scheduled for this day.

### Lesson Object (Core Domain)
> [!IMPORTANT]
> **Subgroups & Parallel Lessons UI Guidance:**  
> Multiple `Lesson` objects can share the exact same `time` and `subject`. This represents parallel subgroups (e.g., one instructor takes half the students in room 403, while another instructor teaches the second subgroup in room 407).  
> The client UI should group these entries into a single time-slot card. **Do NOT use horizontal swipeable carousels for parallel subgroups.** Instead, render them as vertical rows (one row per instructor/room) within the card so students can view all subgroups at a glance.

```json
{
  "id": "09-642 (1)-685",
  "subject": "Физика",
  "rawText": "Физика. Соловьев О.В. Клековкина В.В., ауд. 706,707(Кремл. 16А)",
  "teacher": "Соловьев О.В.",
  "room": "706",
  "building": "Кремл. 16А",
  "type": "other",
  "url": "",
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
- **`subject`**: Cleaned discipline name stripped of teacher names, rooms, and week ranges.
- **`rawText`**: The original unparsed chunk from the Excel cell. Useful for fallback tooltips or debugging.
- **`teacher`**: Name of instructor(s). Multiple co-instructors teaching the same subgroup together are comma-separated (e.g. `Соловьев О.В., Клековкина В.В.`).
- **`room`**: Room / classroom number. If multiple rooms are allocated, they are comma-separated (e.g. `706,707`).
- **`building`**: Campus building name (e.g. `Кремл. 16А`, `Кремл. 35`, `УНИКС`, `Межлаука 1`).
- **`type`**: Lesson classification enum:
  - `"lecture"`: Lecture
  - `"practice"`: Practical session / seminar / physical education
  - `"lab"`: Laboratory class
  - `"distance"`: Remote / distance class
  - `"eor"`: Electronic Educational Resource
  - `"cor"`: Digital Educational Resource (edu.kpfu.ru)
  - `"other"`: Unspecified / general lesson type
- **`url`**: Direct URL for online meetings (e.g. VK Calls, Yandex Telemost) or course portal. Empty string `""` when not applicable.
- **`isAdditional`**: Boolean. `true` if marked as an additional elective lesson (suffix `- д.`).
- **`weekType`**: Recurrence / parity enum:
  - `"all"`: Every week
  - `"odd"`: Odd calendar weeks only (нечетные недели)
  - `"even"`: Even calendar weeks only (четные недели)
  - `"first_half"`: First half of semester (weeks 1–9)
  - `"second_half"`: Second half of semester (weeks 10–18)
- **`weekStart` / `weekEnd`**: Active academic week boundaries (typically `1` and `18`).
- **`time` / `timeStart` / `timeEnd`**: Lesson time interval strings (`HH:MM`).

---

## Curriculum Data Structure (API Reference)

Automated parser and provider for official study plans and curriculum specifications for:
- **IVMIIT:** `curriculum_ivmiit.json` (`facultyId: 9`, 14 fields of study)
- **Institute of Physics:** `curriculum_physics.json` (`facultyId: 6`, 16 fields of study)

Curriculum files cover all active admission cohorts across Bachelor's, Specialist, and Master's degree programs.

### Root Object
```json
{
  "version": 1,
  "facultyId": 9,
  "faculty": "Институт вычислительной математики и информационных технологий",
  "updatedAt": "2026-09-22T11:47:24Z",
  "specialitiesCount": 14,
  "plansCount": 49,
  "plans": [ ... ]
}
```
- `version`: Integer schema version.
- `facultyId`: KFU internal faculty ID (`9` for IVMIIT, `6` for Institute of Physics).
- `faculty`: Full institute title.
- `updatedAt`: ISO 8601 generation timestamp.
- `specialitiesCount`: Total number of academic majors.
- `plansCount`: Total number of study plans parsed.
- `plans`: Array of `Plan` objects.

### Plan Object
```json
{
  "id": "71315",
  "name": "(Информационные системы и технологии) очное 2026г.",
  "profile": "Информационные системы и технологии",
  "year": 2026,
  "form": "очное",
  "specialityId": "6557",
  "specialityCode": "09.03.02",
  "specialityName": "Информационные системы и технологии",
  "degree": "бакалавриат",
  "totalCourses": 4,
  "topLevelCount": 60,
  "disciplines": [ ... ]
}
```
- `id`: Internal KFU plan ID.
- `name`: Full plan title (track, study mode, admission year).
- `profile`: Educational track / profile.
- `year`: Year of admission (e.g. `2026`, `2025`, `2024`).
- `form`: Study format (`очное`, `заочное`, `очно-заочное`).
- `specialityCode`: National program code (e.g. `01.03.02`, `03.03.02`, `09.03.02`, `10.05.03`).
- `specialityName`: Field of study / major name.
- `degree`: Academic degree (`бакалавриат`, `магистратура`, `специалитет`).
- `totalCourses`: Total duration in academic years (`4` for Bachelor, `2` for Master, `5` or `6` for Specialist).
- `disciplines`: Array of top-level `Discipline` items.

### Discipline Hierarchy (`isBlock` & `childDisciplines`)

> [!IMPORTANT]
> **Course Blocks and Elective Modules:**  
> In KFU curriculum plans, disciplines are often grouped under common module prefixes:
> 1. **Modular Subject Blocks:** E.g., parent block `Б1.О.01` (*Humanities Module*), encompassing `Б1.О.01.01` (*Foreign Language*), `Б1.О.01.02` (*Professional English*), `Б1.О.01.03` (*History of Russia*).
> 2. **Technical & Programming Blocks:** E.g., `Б1.О.12` (*Computer Science*), containing `Б1.О.12.01` (*Information Technologies*) and `Б1.О.12.02` (*Programming*).
> 3. **Elective Choices:** E.g., `Б1.В.ДВ.02` (*Elective Pool 2*), containing elective courses `Б1.В.ДВ.02.01` and `Б1.В.ДВ.02.02`.
>
> **JSON Representation:**
> - **Parent Block / Group:**
>   - `isBlock`: `true`
>   - `parentCode`: `null`
>   - `childDisciplines`: Array of child discipline objects.
> - **Child Discipline in a Block:**
>   - Contained inside `childDisciplines` of the parent block.
>   - `isBlock`: `false`
>   - `parentCode`: Parent block code (e.g. `"Б1.О.12"`).
> - **Standalone Discipline:**
>   - `isBlock`: `false`
>   - `parentCode`: `null`
>   - `childDisciplines`: `[]`

```json
{
  "code": "Б1.В.ДВ.09",
  "name": "Дисциплины  по выбору Б1.В.ДВ.9",
  "section": "Дисциплины (модули)",
  "totalHours": 72,
  "auditoryHours": 36,
  "lectures": 0,
  "practices": 36,
  "labs": 0,
  "selfStudy": 36,
  "controlHours": 0,
  "semesters": [],
  "isBlock": true,
  "parentCode": null,
  "childDisciplines": [
    {
      "code": "Б1.В.ДВ.09.01",
      "name": "Введение в информационную безопасность",
      "section": "Дисциплины (модули)",
      "totalHours": 72,
      "auditoryHours": 36,
      "lectures": 0,
      "practices": 36,
      "labs": 0,
      "selfStudy": 36,
      "controlHours": 0,
      "isBlock": false,
      "parentCode": "Б1.В.ДВ.09",
      "childDisciplines": [],
      "semesters": [
        {
          "course": 1,
          "semester": 1,
          "lectures": 0,
          "practices": 36,
          "labs": 0,
          "exam": false,
          "credit": true
        }
      ]
    },
    {
      "code": "Б1.В.ДВ.09.02",
      "name": "Вопросы интеллектуальной собственности и лицензирования программных продуктов",
      "section": "Дисциплины (модули)",
      "totalHours": 72,
      "isBlock": false,
      "parentCode": "Б1.В.ДВ.09",
      "childDisciplines": [],
      "semesters": [
        {
          "course": 1,
          "semester": 1,
          "lectures": 0,
          "practices": 36,
          "labs": 0,
          "exam": false,
          "credit": true
        }
      ]
    }
  ]
}
```

### Semester Breakdown Object
Each entry in the `semesters` array includes:
- `course`: Course year (`1`..`6`).
- `semester`: Global semester number (`1`..`12`).
- `lectures`: Lecture hours allocated for this semester.
- `practices`: Practice / seminar hours.
- `labs`: Laboratory hours.
- `exam`: `true` if an **examination** (экзамен) is required.
- `credit`: `true` if a **pass/fail test** (зачёт) is required.

---

## Combining Curriculum with Schedule Data

The `subject` property from `schedule.json` or `schedule_physics.json` maps directly to the discipline `name` in `curriculum_ivmiit.json` or `curriculum_physics.json`.  
This allows client applications and bots to enrich the daily schedule with:
- Assessment type for the current semester (**Exam**, **Credit / Pass-Fail**, or none).
- Total academic hours and distribution (lectures, seminars, labs, self-study).
- Grouping of elective options under their parent modular block.

### Lookup Example (TypeScript):
```typescript
interface Discipline {
  code: string;
  name: string;
  isBlock: boolean;
  parentCode: string | null;
  childDisciplines?: Discipline[];
  semesters: Array<{
    course: number;
    semester: number;
    lectures: number;
    practices: number;
    labs: number;
    exam: boolean;
    credit: boolean;
  }>;
}

function findDiscipline(plan: { disciplines: Discipline[] }, subjectName: string): Discipline | null {
  const norm = (s: string) => s.toLowerCase().trim();
  const target = norm(subjectName);

  for (const disc of plan.disciplines) {
    if (norm(disc.name) === target) return disc;
    if (disc.isBlock && disc.childDisciplines) {
      for (const child of disc.childDisciplines) {
        if (norm(child.name) === target) return child;
      }
    }
  }
  return null;
}

// Usage example:
const discipline = findDiscipline(plan, lesson.subject);
if (discipline) {
  const semInfo = discipline.semesters.find((s) => s.semester === currentSemester);
  const controlType = semInfo?.exam ? "Exam" : semInfo?.credit ? "Credit (Pass/Fail)" : "None";
  console.log(`${lesson.subject}: assessment method -> ${controlType}`);
}
```
