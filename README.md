# Schedule KFU Data Provider

Automated schedule provider and curriculum parser for:
- **Institute of Computational Mathematics and Information Technologies (IVMIIT / ИВМиИТ)**
- **Institute of Physics (Институт физики)**
at Kazan Federal University (KFU).

## API Endpoints

### 📅 Schedule Endpoints

#### ИВМиИТ (IVMIIT):
- **Full Schedule (GitHub Pages):**
  `https://schedule-kfu.github.io/schedule-data/schedule.json`
- **Raw GitHub Endpoint:**
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/schedule.json`

#### Институт физики (Physics):
- **Full Schedule (GitHub Pages):**
  `https://schedule-kfu.github.io/schedule-data/schedule_physics.json`
- **Raw GitHub Endpoint:**
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/schedule_physics.json`

### 📚 Curriculum Endpoints (Учебные планы)

#### ИВМиИТ (IVMIIT):
- **Full Curriculum (GitHub Pages):**
  `https://schedule-kfu.github.io/schedule-data/curriculum_ivmiit.json`
- **Raw GitHub Endpoint:**
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/curriculum_ivmiit.json`

#### Институт физики (Physics):
- **Full Curriculum (GitHub Pages):**
  `https://schedule-kfu.github.io/schedule-data/curriculum_physics.json`
- **Raw GitHub Endpoint:**
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/curriculum_physics.json`

## Automated Updates

The schedule and curriculum plans are automatically updated twice daily (06:00 and 22:00 MSK) directly from `kpfu.ru` via GitHub Actions.

## Data Structure (Schedule API Reference)

This section describes the structure of `schedule.json` and `schedule_physics.json` for frontend and mobile app developers. The files provide a highly normalized and cleaned representation of the KFU schedule.

> [!NOTE]
> **Различия институтов:**
> - **ИВМиИТ**: номера групп формата `09-xxx` (например, `09-441`, `09-122`). Основной учебный корпус — `Кремл. 35` (Второй высотный корпус).
> - **Институт физики**: номера групп формата `06-xxx` (например, `06-401`, `06-601`, `06-502`). Основной учебный корпус — `Кремл. 16А` (Высотный корпус физиков), педагогические группы занимаются также на `Межлаука 1`, обсерватория — `Астрономическая 18`.

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
- **`subject`**: Cleaned name of the discipline without teachers, rooms, or week numbers.
- **`rawText`**: The original unparsed chunk of text from the Excel cell. Useful for debugging or showing as a fallback tooltip.
- **`teacher`**: Name of the teacher(s). If multiple teachers teach the *same* subgroup together, they are separated by a comma (e.g. `Соловьев О.В., Клековкина В.В.`).
- **`room`**: Room number. If a subgroup spans multiple rooms, they are separated by commas (e.g., `706,707`).
- **`building`**: The building name (e.g., `Кремл. 35`, `УНИКС`).
- **`type`**: Type of the lesson. Enum:
  - `"lecture"`: Лекция (включая поточные лекционные залы 1-2 этажей)
  - `"practice"`: Практическое занятие (включая аудитории верхних этажей и физкультуру)
  - `"lab"`: Лабораторная работа
  - `"distance"`: Дистанционное занятие
  - `"eor"`: ЭОР (Электронный образовательный ресурс)
  - `"cor"`: ЦОР (Цифровой образовательный ресурс на базе edu.kpfu.ru)
  - `"other"`: Другое (тип не указан явно и не может быть определен по аудитории)
- **`url`**: String. Direct link for online meetings (e.g., VK Calls `https://vk.ru/call/...`, Yandex Telemost `https://telemost.yandex.ru/...`) or learning portal (`https://edu.kpfu.ru`). Empty string `""` if not applicable.
- **`isAdditional`**: Boolean. `true` if the lesson is marked as "дополнительная пара" (suffix `- д.`). The UI might want to highlight these differently.
- **`weekType`**: Describes the parity/recurrence of the lesson. Enum:
  - `"all"`: Every week
  - `"odd"`: Odd weeks only (нечетные, н/н)
  - `"even"`: Even weeks only (четные, ч/н)
  - `"first_half"`: First half of the semester (weeks 1-9)
  - `"second_half"`: Second half of the semester (weeks 10-18)
- **`weekStart` / `weekEnd`**: Integer bounds for the weeks this lesson is active. Usually `1` and `18`.
- **`time` / `timeStart` / `timeEnd`**: String representations of the lesson's time schedule. Automatically overrides standard university time-slots if a custom time is specified in the Excel file (e.g., for sports in UNICS).

---

# Curriculum KFU Data Provider (Учебные планы ИВМиИТ и Института физики)

Automated parser and provider for official study plans and curriculum specifications for degree programs at IVMIIT (`curriculum_ivmiit.json`) and Institute of Physics (`curriculum_physics.json`) at KFU.

## Curriculum Endpoints

#### ИВМиИТ (IVMIIT):
- **Full Curriculum (GitHub Pages):**  
  `https://schedule-kfu.github.io/schedule-data/curriculum_ivmiit.json`
- **Raw GitHub Endpoint:**  
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/curriculum_ivmiit.json`

#### Институт физики (Physics):
- **Full Curriculum (GitHub Pages):**  
  `https://schedule-kfu.github.io/schedule-data/curriculum_physics.json`
- **Raw GitHub Endpoint:**  
  `https://raw.githubusercontent.com/Schedule-KFU/schedule-data/main/curriculum_physics.json`

## Curriculum Data Structure (API Reference)

The `curriculum_ivmiit.json` and `curriculum_physics.json` files contain structured curriculum data across all active admission years (Бакалавриат, Специалитет, Магистратура).
- **ИВМиИТ**: `facultyId: 9`, 14 направлений подготовки.
- **Институт физики**: `facultyId: 6`, 16 направлений подготовки (`03.03.02` Физика, `03.03.03` Радиофизика, `03.05.01` Астрономия, `10.03.01` ИБ, `21.03.03` Геодезия, `27.03.05` Инноватика, `28.03.01` Нанотехнологии, `44.03.05` Педобразование и др.).

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
- `version`: Integer version of the curriculum schema.
- `facultyId`: KFU internal faculty ID (`9` for IVMIIT).
- `faculty`: Full name of the institute.
- `updatedAt`: ISO 8601 timestamp of generation.
- `specialitiesCount`: Total number of majors in the institute.
- `plansCount`: Total number of parsed curriculum plans.
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
- `name`: Full description of the plan (track, form, admission year).
- `profile`: Educational profile / track.
- `year`: Year of admission (e.g. `2026`, `2025`, `2024`, `2023`).
- `form`: Form of education (`очное`, `заочное`, `очно-заочное`).
- `specialityCode`: All-Russian major code (e.g. `01.03.02`, `09.03.02`, `10.03.01`).
- `specialityName`: Name of the major / direction.
- `degree`: Educational degree (`бакалавриат`, `магистратура`, `специалитет`).
- `totalCourses`: Total years of study (`4` for bachelor, `2` for master).
- `disciplines`: Array of top-level `Discipline` objects.

### Discipline Object & Hierarchy (`isBlock` & `childDisciplines`)

> [!IMPORTANT]
> **Объединённые блоки и группы по выбору:**  
> В учебных планах КФУ некоторые предметы объединены в общие блоки с единым префиксом кода:
> 1. **Модули и блоки дисциплин** (например, родительский блок `Б1.О.01` *«Гуманитарный блок»*, в который входят `Б1.О.01.01` *«Иностранный язык»*, `Б1.О.01.02` *«Деловой иностранный язык для программистов»*, `Б1.О.01.03` *«История России»* и др.).
> 2. **Блоки программирования и технологий** (например, `Б1.О.03` *«Программирование»*, объединяющий `Б1.О.03.01` *«Основы программирования»*, `Б1.О.03.02` *«ООП»* и т.д.).
> 3. **Дисциплины по выбору (элективы)** (например, `Б1.В.ДВ.02` *«Дисциплины по выбору Б1.В.ДВ.2»*, содержащий варианты выбора `Б1.В.ДВ.02.01` и `Б1.В.ДВ.02.02`).
>
> **Как это представлено в JSON:**
> - Если дисциплина является родительским блоком/группой:
>   - `isBlock`: `true`
>   - `parentCode`: `null`
>   - `childDisciplines`: массив входящих в группу предметов.
> - Если дисциплина входит в блок:
>   - Находится внутри `childDisciplines` родительского блока.
>   - `isBlock`: `false`
>   - `parentCode`: код родительского блока (например, `"Б1.О.01"`).
> - Если дисциплина самостоятельная (не входит в блок):
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
Каждый элемент массива `semesters`:
- `course`: Номер курса (`1`..`4`).
- `semester`: Сквозной номер семестра (`1`..`8`).
- `lectures`: Часы лекций в данном семестре.
- `practices`: Часы практических занятий.
- `labs`: Часы лабораторных работ.
- `exam`: `true`, если в семестре по предмету предусмотрен **экзамен**.
- `credit`: `true`, если в семестре по предмету предусмотрен **зачёт**.

---

## Использование совместно с расписанием (`schedule.json` / `schedule_physics.json`)

Поле `subject` из `schedule.json` (или `schedule_physics.json`) соответствует полю `name` дисциплины в `curriculum_ivmiit.json` (или `curriculum_physics.json`).  
Это позволяет приложению или боту обогащать расписание:
- Показывать, есть ли по предмету **экзамен** или **зачёт** в текущем семестре.
- Показывать общее количество часов и распределение (лекции/практики/лабы).
- Группировать элективы по родительскому блоку `parentCode`.

### Пример поиска дисциплины (TypeScript / JavaScript):
```typescript
function findDiscipline(curriculumPlan: any, subjectName: string) {
  const norm = (s: string) => s.toLowerCase().trim();
  const target = norm(subjectName);

  for (const disc of curriculumPlan.disciplines) {
    if (norm(disc.name) === target) return disc;
    if (disc.isBlock && disc.childDisciplines) {
      for (const child of disc.childDisciplines) {
        if (norm(child.name) === target) return child;
      }
    }
  }
  return null;
}

// Пример использования:
const discipline = findDiscipline(plan, lesson.subject);
if (discipline) {
  const semInfo = discipline.semesters.find((s: any) => s.semester === currentSemester);
  const controlType = semInfo?.exam ? "Экзамен" : semInfo?.credit ? "Зачет" : "—";
  console.log(`${lesson.subject}: форма контроля — ${controlType}`);
}
```
