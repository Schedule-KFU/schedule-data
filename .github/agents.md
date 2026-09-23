# AGENTS.md — Agent & Contributor Guidelines

This document provides instructions, architectural context, and coding standards for AI agents and human contributors working within the `schedule-data` repository.

---

## 1. Project Overview & Architecture

`schedule-data` is the automated backend data provider for Kazan Federal University (KFU) schedule and curriculum applications, including:
- **Android App:** [`schedule-android`](file:///Users/ost/Documents/GitHub/schedule-android)
- **Apple (iOS / macOS) App:** [`schedule-swift`](file:///Users/ost/Documents/GitHub/schedule-swift)
- Telegram/VK bots and web clients.

The repository scrapes, cleans, normalizes, and publishes static JSON data through GitHub Pages and GitHub Raw endpoints.

---

## 2. Supported Institutes & File Map

| Institute | Schedule Source | Schedule Parser | Output Schedule | Curriculum Parser | Output Curriculum | Faculty ID | Group Prefix |
|---|---|---|---|---|---|---|---|
| **IVMIIT** | `kpfu.ru/...` (.xlsx) | `parser.py` | `schedule.json` | `curriculum_parser.py` | `curriculum_ivmiit.json` | `9` | `09-xxx` |
| **Physics** | `kpfu.ru/physics/raspisanie-zanyatij` (.xlsx) | `parser_physics.py` | `schedule_physics.json` | `curriculum_parser_physics.py` | `curriculum_physics.json` | `6` | `06-xxx` |

### Automation:
- **GitHub Actions Workflow:** [`.github/workflows/update_schedule.yml`](file:///Users/ost/Documents/GitHub/schedule-data/.github/workflows/update_schedule.yml) runs twice daily (`03:00` and `19:00` UTC). It executes all parsers, stages output `.json` files, and pushes changes with `[skip ci]`.

---

## 3. Strict Development Rules

### Rule 1: Language & Communication Policy
- **Agent Communication with the User:** The AI agent MUST always communicate, explain, and reply to the user in **Russian** (`ru-RU`), unless the user explicitly requests another language.
- **English-First Development & Zero Hardcoded Strings:**
  - All user-facing UI text, strings, and resources MUST be designed and implemented in **English first** (in default `values/strings.xml`, `Localizable.xcstrings`, UI labels, accessibility text).
  - Russian translations (`values-ru/strings.xml`, Russian string catalogs) are added **only after** the English version is fully in place.
  - **NEVER use hardcoded string literals in UI code:** Every user-facing label or text in Composable or SwiftUI views MUST use string resource keys (`R.string.<key>` or `String(localized: ...)`).
- **Repository Documentation in English:** `README.md`, architectural guides, commit messages, and code comments must remain strictly in clear English.
- Russian in code/data is permitted **only** for literal university domain data values (e.g. subject names, instructor names, classroom labels like `"Кремл. 16А"` or `"1 курс"`).

### Rule 2: Modular Institute Parsers
- Keep institute-specific parsers in **separate files** (e.g. `parser.py` vs `parser_physics.py`).
- Different institutes use distinct sheet naming, column placements, and formatting quirks. Do not merge them into monolithic, brittle single-file parsers unless explicitly requested.

### Rule 3: Resilient Network Fetching
- KFU servers (`kpfu.ru` and `shelly.kpfu.ru`) frequently suffer from high latency or intermittent timeouts.
- All HTTP requests must use timeouts (20–35s) and automatic retry loops (minimum 3 attempts with exponential/linear backoff).
- Shelley KFU web pages use `windows-1251` encoding. Ensure explicit decoding (`errors='replace'`).

### Rule 4: Data Schema & Downstream Compatibility
- Mobile clients rely directly on the JSON schema. **Never change existing field names or types without explicit cross-repository coordination.**
- **Schedule Schema (`schedule*.json`):**
  - Group identifiers must preserve full text with subgroup suffixes (e.g. `"09-642 (1)"`).
  - Lessons at the same time and subject indicate parallel subgroups: client apps display them vertically.
  - Lesson types must conform to the enum: `"lecture"`, `"practice"`, `"lab"`, `"distance"`, `"eor"`, `"cor"`, `"other"`.
- **Curriculum Schema (`curriculum*.json`):**
  - Course blocks and elective pools must preserve hierarchy:
    - Parent blocks: `isBlock: true`, `parentCode: null`, `childDisciplines: [...]`.
    - Child items: `isBlock: false`, `parentCode: "<block_code>"`.
    - Standalone items: `isBlock: false`, `parentCode: null`, `childDisciplines: []`.
  - Include semester breakdown with exams (`exam: boolean`) and credits (`credit: boolean`).

### Rule 5: Clean Repository & Git Hygiene
- Output JSON files must use 2-space indentation with `ensure_ascii=False` to preserve readable Cyrillic characters.
- Never commit virtual environment directories (`.venv/`), downloaded `.xlsx` spreadsheets, or Python bytecode (`__pycache__/`, `*.pyc`). Check `.gitignore` before committing.

---

## 4. Communication & Engineering Culture
- **Peer-to-peer collaboration:** Provide direct, objective engineering solutions. Evaluate technical trade-offs honestly without sugarcoating or conversational filler.
- **Focus on correctness & verification:** Always test parsers against real KFU data before concluding tasks. Verify output size, item counts, and schema conformance.
