import sys
import os
import re
import json
import tempfile
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    requests = None

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DAYS_ORDER = [
    ("понедельник", 1),
    ("вторник", 2),
    ("среда", 3),
    ("четверг", 4),
    ("пятница", 5),
    ("суббота", 6)
]

TEACHER_PATTERN = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ]\.(?:\s*[А-ЯЁ]\.?)?"

def compute_semester_string():
    now = datetime.now()
    month = now.month
    year = now.year
    is_autumn = month >= 9 or month <= 1
    sem_num = 1 if is_autumn else 2
    acad_start = year if month >= 9 else year - 1
    acad_end = acad_start + 1
    return f"{sem_num} семестр {acad_start}/{acad_end}"

def compute_semester_meta(ref_date=None):
    now = ref_date or datetime.now()
    month = now.month
    year = now.year
    is_autumn = month >= 9 or month <= 1
    sem_num = 1 if is_autumn else 2
    acad_start = year if month >= 9 else year - 1
    acad_end = acad_start + 1

    if is_autumn:
        # Autumn starts week of Sept 1
        sept1 = datetime(acad_start, 9, 1)
        start_monday = sept1 - timedelta(days=sept1.weekday())
        end_date = datetime(acad_end, 1, 25)
    else:
        # Spring starts first Monday of February
        feb1 = datetime(acad_end, 2, 1)
        days_to_monday = (7 - feb1.weekday()) % 7 if feb1.weekday() != 0 else 0
        start_monday = feb1 + timedelta(days=days_to_monday)
        end_date = datetime(acad_end, 6, 30)

    return {
        "semesterNumber": sem_num,
        "academicYear": f"{acad_start}/{acad_end}",
        "startDate": start_monday.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "academicWeeksCount": 18,
        "weekParityRule": "odd_first"
    }

def get_latest_xlsx_url(web_url, headers=HEADERS, exclude_keywords=None, retries=3):
    if exclude_keywords is None:
        exclude_keywords = ["peresdach", "sessii", "zachet", "komissij", "zachislenie", "praktik", "dop"]

    html = ""
    for attempt in range(retries):
        try:
            if requests is not None:
                resp = requests.get(web_url, headers=headers, timeout=35)
                resp.encoding = resp.apparent_encoding
                html = resp.text
            else:
                import urllib.request
                req = urllib.request.Request(web_url, headers=headers)
                with urllib.request.urlopen(req, timeout=35) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
            if html:
                break
        except Exception as e:
            print(f"[Warning] Attempt {attempt+1}/{retries} to fetch {web_url} failed: {e}", file=sys.stderr)
            if attempt < retries - 1:
                import time
                time.sleep(2)

    pattern = r'href=["\'](https?://kpfu\.ru/portal/docs/[^"\']*?\.xlsx)["\']'
    matches = re.findall(pattern, html, flags=re.IGNORECASE)

    for m in matches:
        m_low = m.lower()
        if "raspisanie" in m_low and any(k in m_low for k in ["sem", "семестр", "kurs", "курс", "zanyatij"]):
            if not any(ex in m_low for ex in exclude_keywords):
                return m

    for m in matches:
        m_low = m.lower()
        if "raspisanie" in m_low and not any(ex in m_low for ex in exclude_keywords):
            return m

    for m in matches:
        if "raspisanie" in m.lower():
            return m

    if matches:
        return matches[0]
    return None

def download_file(url, local_path, headers=HEADERS, retries=3):
    for attempt in range(retries):
        try:
            if requests is not None:
                r = requests.get(url, headers=headers, timeout=45)
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(r.content)
            else:
                import urllib.request
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=45) as resp:
                    with open(local_path, "wb") as f:
                        f.write(resp.read())
            return True
        except Exception as e:
            print(f"[Warning] Download attempt {attempt+1}/{retries} failed: {e}", file=sys.stderr)
            if attempt < retries - 1:
                import time
                time.sleep(2)
    return False

def extract_teachers(text):
    return re.findall(TEACHER_PATTERN, text)

def extract_url(text):
    url_match = re.search(r"https?://[^\s,\);]+", text)
    if url_match:
        return url_match.group(0).strip(" .,;")
    elif "edu.kpfu.ru" in text.lower():
        return "https://edu.kpfu.ru"
    return ""

def preserve_lesson_ids(database, previous):
    """Preserve existing lesson IDs across runs based on group, day, time, subject, teacher, room."""
    if not previous or not isinstance(previous, dict):
        return

    def entries(data):
        for group in data.get("groups", []):
            for day in group.get("days", []):
                for lesson in day.get("lessons", []):
                    yield group, day, lesson

    def key(group, day, lesson):
        return (
            group.get("id", group.get("group")),
            day.get("dayIndex"),
            lesson.get("timeStart"),
            lesson.get("timeEnd"),
            lesson.get("subject"),
            lesson.get("teacher"),
            lesson.get("room")
        )

    old_ids = defaultdict(deque)
    used = set()
    max_number = 0
    for group, day, lesson in entries(previous):
        identifier = str(lesson.get("id", ""))
        if identifier:
            old_ids[key(group, day, lesson)].append(identifier)
            used.add(identifier)
            match = re.search(r'-(\d+)$', identifier)
            if match:
                max_number = max(max_number, int(match.group(1)))

    for group, day, lesson in entries(database):
        candidates = old_ids[key(group, day, lesson)]
        if candidates:
            lesson["id"] = candidates.popleft()
        else:
            while True:
                max_number += 1
                identifier = f"{group.get('id', group.get('group', 'lesson'))}-{max_number}"
                if identifier not in used:
                    used.add(identifier)
                    lesson["id"] = identifier
                    break

def save_database_with_cache_check(db, output_file):
    output_path = os.fspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file))
    groups = db.get("groups", [])
    lessons = sum(len(d.get("lessons", [])) for g in groups for d in g.get("days", []))
    if not groups or not lessons:
        raise ValueError(f"Schedule {output_file} is empty; previous output was preserved")

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as existing_f:
                existing_db = json.load(existing_f)

            preserve_lesson_ids(db, existing_db)

            old_groups = existing_db.get("groups", [])
            old_lessons = sum(len(d.get("lessons", [])) for g in old_groups for d in g.get("days", []))
            if old_groups and len(groups) < len(old_groups) * 0.7:
                raise ValueError(f"Schedule shrank suspiciously: groups {len(old_groups)} -> {len(groups)}")
            if old_lessons and lessons < old_lessons * 0.7:
                raise ValueError(f"Schedule shrank suspiciously: lessons {old_lessons} -> {lessons}")

            if {k: v for k, v in existing_db.items() if k != "updatedAt"} == {k: v for k, v in db.items() if k != "updatedAt"}:
                db["updatedAt"] = existing_db.get("updatedAt", db.get("updatedAt"))
                print(f"✅ Schedule content is identical to existing {output_file}. Preserving updatedAt timestamp.")
            else:
                print(f"🔄 Schedule changes detected! Updated timestamp: {db['updatedAt']}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            print(f"Warning: Failed to compare with existing {output_file}: {e}")

    directory = os.path.dirname(os.path.abspath(output_path))
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as stream:
            temporary_path = stream.name
            json.dump(db, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)

    total_lessons = sum(len(d['lessons']) for g in db['groups'] for d in g['days'])
    print(f"Success! Saved {len(db['groups'])} groups and {total_lessons} lessons to {output_file}")
