import sys
import os
import re
import json
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    requests = None

FACULTY_ID = 9
FACULTY_NAME = "Институт вычислительной математики и информационных технологий"
BASE_URL = "https://shelly.kpfu.ru/e-ksu/study_plan_for_web"
OUTPUT_FILE = "curriculum_ivmiit.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

def fetch_url(url, post_data=None, retries=3, backoff=1.5):
    for attempt in range(retries):
        try:
            if requests:
                if post_data is not None:
                    resp = requests.post(url, data=post_data, headers=HEADERS, timeout=20)
                else:
                    resp = requests.get(url, headers=HEADERS, timeout=20)
                resp.encoding = "windows-1251"
                return resp.text
            else:
                import urllib.request
                import urllib.parse
                if post_data is not None:
                    encoded_data = urllib.parse.urlencode(post_data).encode("windows-1251")
                    req = urllib.request.Request(
                        url,
                        data=encoded_data,
                        headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"}
                    )
                else:
                    req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = resp.read()
                    return raw.decode("windows-1251", errors="replace")
        except Exception as e:
            if attempt == retries - 1:
                print(f"    [Error] Request failed for {url} after {retries} attempts: {e}", file=sys.stderr)
                return None
            time.sleep(backoff * (attempt + 1))
    return None

def clean_html(text):
    return re.sub(r'<[^>]+>', '', text).replace('&nbsp;', ' ').strip()

def to_int(val):
    try:
        clean = re.sub(r'[^\d]', '', str(val))
        return int(clean) if clean else 0
    except (ValueError, TypeError):
        return 0

def parse_specialities():
    url = f"{BASE_URL}?p_faculty={FACULTY_ID}"
    html = fetch_url(url)
    if not html:
        return []

    # p_speciality select
    m = re.search(r'<select\b[^>]*name=[\"\']?p_speciality[\"\']?[^>]*>(.*?)</select>', html, re.DOTALL | re.I)
    if not m:
        return []

    specialities = []
    options = re.findall(r'<option\b[^>]*value=[\"\']?(\d+)[\"\']?[^>]*>(.*?)</option>', m.group(1), re.DOTALL | re.I)
    for spec_id, raw_label in options:
        label = clean_html(raw_label)
        # Match pattern: 01.03.02 Прикладная математика и информатика (направление)
        match = re.match(r'^([\d\.]+)\s+(.*?)(?:\s*\((.*?)\))?$', label)
        if match:
            code = match.group(1).strip()
            name = match.group(2).strip()
            degree_type = match.group(3).strip() if match.group(3) else ""
        else:
            code = ""
            name = label
            degree_type = ""

        # Normalize degree
        degree = "бакалавриат"
        deg_low = (degree_type + " " + name).lower()
        if "магистр" in deg_low or (code and code.split('.')[1] == '04'):
            degree = "магистратура"
        elif "специал" in deg_low or (code and code.split('.')[1] == '05'):
            degree = "специалитет"
        elif "аспирант" in deg_low or (code and code.split('.')[1] == '06'):
            degree = "аспирантура"
        elif code and code.split('.')[1] == '03':
            degree = "бакалавриат"

        specialities.append({
            "id": spec_id,
            "code": code,
            "name": name,
            "rawLabel": label,
            "degree": degree
        })

    return specialities

def parse_plans_for_speciality(spec_id):
    url = f"{BASE_URL}?p_faculty={FACULTY_ID}&p_speciality={spec_id}"
    html = fetch_url(url)
    if not html:
        return []

    m = re.search(r'<select\b[^>]*name=[\"\']p_sp[\"\'][^>]*>(.*?)</select>', html, re.DOTALL | re.I)
    if not m:
        return []

    plans = []
    options = re.findall(r'<option\b[^>]*value=[\"\']?(\d+)[\"\']?[^>]*>(.*?)</option>', m.group(1), re.DOTALL | re.I)
    for plan_id, raw_label in options:
        label = clean_html(raw_label)
        # Example: (Прикладная математика и информатика) очное 2026г.
        year_match = re.search(r'(\d{4})г?', label)
        year = int(year_match.group(1)) if year_match else None

        form = "очное"
        if "заочн" in label.lower():
            form = "заочное" if "очно-заочн" not in label.lower() else "очно-заочное"

        profile_match = re.search(r'\((.*?)\)', label)
        profile = profile_match.group(1).strip() if profile_match else ""

        plans.append({
            "id": plan_id,
            "name": label,
            "profile": profile,
            "year": year,
            "form": form
        })

    return plans

def parse_study_plan_tables(spec_id, plan_id):
    post_data = {
        "p_faculty": str(FACULTY_ID),
        "p_portal": "",
        "p_speciality": str(spec_id),
        "p_sp": str(plan_id),
        "p_course": "0"
    }
    html = fetch_url(BASE_URL, post_data=post_data)
    if not html:
        return []

    clean_markup = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    tables = re.findall(r'<table\b[^>]*>.*?</table>', clean_markup, flags=re.DOTALL | re.IGNORECASE)
    if len(tables) <= 1:
        # Table 0 is the search form, no course tables exist
        return []

    course_tables = tables[1:]
    disciplines_by_code = {}

    for course_idx, table_html in enumerate(course_tables, 1):
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', table_html, flags=re.DOTALL | re.IGNORECASE)
        if len(rows) < 3:
            continue

        # Header Row 0: ['N', 'Название дисциплины', 'Всего', ..., '1 курс']
        r0 = [clean_html(c) for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', rows[0], flags=re.DOTALL | re.I)]
        course_num = course_idx
        for c in r0:
            cm = re.search(r'(\d+)\s*курс', c, re.I)
            if cm:
                course_num = int(cm.group(1))

        # Header Row 1: Semesters detection ['Всего', ..., '1 семестр', '2 семестр']
        r1 = [clean_html(c) for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', rows[1], flags=re.DOTALL | re.I)]
        semesters = []
        for c in r1:
            sem_m = re.search(r'(\d+)\s*семестр', c, re.I)
            if sem_m:
                semesters.append(int(sem_m.group(1)))

        current_section = "Дисциплины (модули)"

        for row in rows[3:]:
            cells = [clean_html(c) for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, flags=re.DOTALL | re.I)]
            if len(cells) < 2:
                continue

            code = cells[0].strip()
            name = cells[1].strip()

            # Empty code indicates section title (e.g. "Практика")
            if not code:
                if name:
                    current_section = name
                continue

            total_hours = to_int(cells[2]) if len(cells) > 2 else 0
            aud_hours = to_int(cells[3]) if len(cells) > 3 else 0
            aud_lec = to_int(cells[4]) if len(cells) > 4 else 0
            aud_prac = to_int(cells[5]) if len(cells) > 5 else 0
            aud_lab = to_int(cells[6]) if len(cells) > 6 else 0
            self_study = to_int(cells[7]) if len(cells) > 7 else 0
            control_hours = to_int(cells[8]) if len(cells) > 8 else 0

            sem_list = []
            for s_idx, sem_num in enumerate(semesters):
                base_col = 9 + s_idx * 5
                if base_col + 4 < len(cells):
                    lec = to_int(cells[base_col])
                    prac = to_int(cells[base_col + 1])
                    lab = to_int(cells[base_col + 2])
                    exam = cells[base_col + 3].strip() == '+'
                    credit = cells[base_col + 4].strip() == '+'

                    if lec > 0 or prac > 0 or lab > 0 or exam or credit:
                        sem_list.append({
                            "course": course_num,
                            "semester": sem_num,
                            "lectures": lec,
                            "practices": prac,
                            "labs": lab,
                            "exam": exam,
                            "credit": credit
                        })

            if code not in disciplines_by_code:
                disciplines_by_code[code] = {
                    "code": code,
                    "name": name,
                    "section": current_section,
                    "totalHours": total_hours,
                    "auditoryHours": aud_hours,
                    "lectures": aud_lec,
                    "practices": aud_prac,
                    "labs": aud_lab,
                    "selfStudy": self_study,
                    "controlHours": control_hours,
                    "semesters": sem_list,
                    "childDisciplines": []
                }
            else:
                existing_sems = {s["semester"] for s in disciplines_by_code[code]["semesters"]}
                for s in sem_list:
                    if s["semester"] not in existing_sems:
                        disciplines_by_code[code]["semesters"].append(s)
                disciplines_by_code[code]["semesters"].sort(key=lambda x: x["semester"])

    # Build hierarchy: parent blocks & child disciplines
    all_codes = set(disciplines_by_code.keys())
    top_level = []

    for code, disc in disciplines_by_code.items():
        parts = code.split('.')
        parent_code = None
        for i in range(len(parts) - 1, 0, -1):
            cand = '.'.join(parts[:i])
            if cand in all_codes:
                parent_code = cand
                break

        disc["parentCode"] = parent_code
        if parent_code is not None:
            disciplines_by_code[parent_code]["childDisciplines"].append(disc)
            disciplines_by_code[parent_code]["isBlock"] = True
        else:
            top_level.append(disc)

    for disc in disciplines_by_code.values():
        if "isBlock" not in disc:
            disc["isBlock"] = False
        if disc["childDisciplines"]:
            disc["childDisciplines"].sort(key=lambda x: x["code"])

    return top_level

def run_parser():
    start_time = time.time()
    print("=== Starting KFU IVMIIT Curriculum Parser ===")
    specialities = parse_specialities()
    print(f"Found {len(specialities)} specialities for faculty {FACULTY_ID} ({FACULTY_NAME})")

    parsed_plans = []
    total_plans_discovered = 0

    for s_idx, spec in enumerate(specialities, 1):
        spec_id = spec["id"]
        spec_code = spec["code"]
        spec_name = spec["name"]
        degree = spec["degree"]

        plans = parse_plans_for_speciality(spec_id)
        total_plans_discovered += len(plans)
        print(f"\n[{s_idx}/{len(specialities)}] {spec_code} {spec_name} ({len(plans)} plans)")

        for plan in plans:
            plan_id = plan["id"]
            plan_name = plan["name"]
            profile = plan["profile"]
            year = plan["year"]
            form = plan["form"]

            print(f"  -> Fetching plan {plan_id}: {plan_name} ...", end="", flush=True)
            disciplines = parse_study_plan_tables(spec_id, plan_id)

            if not disciplines:
                print(" [No table data]")
                continue

            # Count courses and child disciplines
            max_course = 1
            for d in disciplines:
                for s in d.get("semesters", []):
                    if s.get("course", 1) > max_course:
                        max_course = s.get("course", 1)
                for c in d.get("childDisciplines", []):
                    for s in c.get("semesters", []):
                        if s.get("course", 1) > max_course:
                            max_course = s.get("course", 1)

            block_count = sum(1 for d in disciplines if d.get("isBlock"))
            child_count = sum(len(d.get("childDisciplines", [])) for d in disciplines if d.get("isBlock"))
            print(f" [OK: {len(disciplines)} top items ({block_count} blocks, {child_count} children), {max_course} courses]")

            parsed_plans.append({
                "id": plan_id,
                "name": plan_name,
                "profile": profile,
                "year": year,
                "form": form,
                "specialityId": spec_id,
                "specialityCode": spec_code,
                "specialityName": spec_name,
                "degree": degree,
                "totalCourses": max_course,
                "topLevelCount": len(disciplines),
                "disciplines": disciplines
            })

            time.sleep(0.1)

    result_data = {
        "version": 1,
        "facultyId": FACULTY_ID,
        "faculty": FACULTY_NAME,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "specialitiesCount": len(specialities),
        "plansCount": len(parsed_plans),
        "plans": parsed_plans
    }

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"\n=== Successfully saved {len(parsed_plans)} study plans to {OUTPUT_FILE} ({file_size_kb:.1f} KB) in {elapsed:.1f}s ===")

if __name__ == "__main__":
    run_parser()
