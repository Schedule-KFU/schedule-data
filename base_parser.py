import sys
import os
import re
import json
from datetime import datetime, timezone

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

TEACHER_PATTERN = r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?"

def compute_semester_string():
    now = datetime.now()
    month = now.month
    year = now.year
    is_autumn = month >= 9 or month <= 1
    sem_num = 1 if is_autumn else 2
    acad_start = year if month >= 9 else year - 1
    acad_end = acad_start + 1
    return f"{sem_num} семестр {acad_start}/{acad_end}"

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

def save_database_with_cache_check(db, output_file):
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file)

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as existing_f:
                existing_db = json.load(existing_f)

            if (existing_db.get("groups") == db.get("groups") and
                existing_db.get("semester") == db.get("semester") and
                existing_db.get("sourceUrl") == db.get("sourceUrl")):
                db["updatedAt"] = existing_db.get("updatedAt", db["updatedAt"])
                print(f"✅ Schedule content is identical to existing {output_file}. Preserving updatedAt timestamp.")
            else:
                print(f"🔄 Schedule changes detected! Updated timestamp: {db['updatedAt']}")
        except Exception as e:
            print(f"Warning: Failed to compare with existing {output_file}: {e}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    total_lessons = sum(len(d['lessons']) for g in db['groups'] for d in g['days'])
    print(f"Success! Saved {len(db['groups'])} groups and {total_lessons} lessons to {output_file}")
