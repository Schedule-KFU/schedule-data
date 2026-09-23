import sys
import os
import re
import json
from datetime import datetime, timezone
import openpyxl

from base_parser import (
    HEADERS,
    DAYS_ORDER,
    get_latest_xlsx_url as base_get_latest_xlsx_url,
    download_file,
    compute_semester_string,
    save_database_with_cache_check
)

PHYSICS_URL = "https://kpfu.ru/physics/raspisanie-zanyatij"
OUTPUT_FILE = "schedule_physics.json"

def get_latest_xlsx_url(retries=3):
    return base_get_latest_xlsx_url(PHYSICS_URL, HEADERS, retries=retries)

def split_cell_into_lesson_texts(text):
    trimmed = text.strip()
    if not trimmed:
        return []
    # Split by semicolon or newline when followed by a new lesson start (e.g. subject or week range or course by choice)
    parts = re.split(r"(?:;\s*(?=\b\d{1,2}[\s\-]*(?:н\b|нед|недел)|\b[А-ЯЁ][а-яё]+)|\n\s*(?=\b\d{1,2}[\s\-]*(?:н\b|нед|недел)|[А-ЯЁ][а-яё]+|Курс\s+по\s+выбору))", trimmed)
    res = [p.strip() for p in parts if p.strip()]
    return res if res else [trimmed]

def parse_lesson_text(txt):
    trimmed = txt.strip()
    if not trimmed:
        return None

    lower = trimmed.lower()
    # Reject signatures, headers, footnotes
    if "____" in trimmed or \
       "департамент образования" in lower or \
       "учебно-методическ" in lower or \
       "утверждаю" in lower or \
       "согласовано" in lower or \
       "поминов" in lower or \
       "турилова" in lower:
        return None

    # Check for online / call URLs
    url_match = re.search(r'(https?://[^\s)"]+)', trimmed)
    url = url_match.group(1).rstrip('.,;') if url_match else ""

    # Week bounds & parity
    week_start = 1
    week_end = 18
    week_type = "all"

    if "ч.н" in lower or "ч/н" in lower or "четн" in lower:
        week_type = "even"
    elif "н.н" in lower or "н/н" in lower or "нечет" in lower:
        week_type = "odd"

    range_match = re.search(r'(?:с\s+)?(\d{1,2})\s*-\s*(\d{1,2})\s*(?:н\b|нед)', trimmed, re.I)
    if range_match:
        week_start = int(range_match.group(1))
        week_end = int(range_match.group(2))
        if week_type == "all":
            if week_start == 1 and week_end == 9:
                week_type = "first_half"
            elif week_start == 10 and week_end == 18:
                week_type = "second_half"
    else:
        single_week = re.search(r'\b(\d{1,2})\s*(?:н\b|нед)', trimmed, re.I)
        if single_week:
            w_val = int(single_week.group(1))
            week_start = w_val
            week_end = w_val

    # Lesson Type
    if "(лаб" in lower or "лаб." in lower or "лаборат" in lower:
        l_type = "lab"
    elif "(пр" in lower or "пр." in lower or "практ" in lower:
        l_type = "practice"
    elif "(л)" in lower or "(л+" in lower or "лек." in lower or "лекция" in lower:
        l_type = "lecture"
    elif "дистанцион" in lower or "онлайн" in lower:
        l_type = "distance"
    elif "эор" in lower:
        l_type = "eor"
    elif "цор" in lower:
        l_type = "cor"
    else:
        l_type = "other"

    is_additional = bool(re.search(r"\s*-\s*д\.?(?:\s|$)", lower))

    # Teachers
    teacher_pattern = r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?"
    teachers = re.findall(teacher_pattern, trimmed)

    # Building & Room
    building = "Кремл. 16А"
    room = ""

    if "межлаука" in lower:
        building = "Межлаука 1"
    elif "лево-булач" in lower or "булач" in lower:
        building = "Лево-Булачная 44"
    elif "лицей" in lower:
        building = "Лицей Лобачевского"
    elif "уникс" in lower:
        building = "УНИКС"
    elif "к.-з." in lower or "к/з" in lower:
        building = "Концертный зал"

    aud_match = re.search(r'ауд\.?\s*([0-9А-Яа-яA-Za-z]+)', trimmed, re.I)
    if aud_match:
        room = aud_match.group(1).strip()
    else:
        # Search for room numbers (3-4 digits like 110, 1309, 806, 907)
        candidate_rooms = [
            m.group(1) for m in re.finditer(r'\b([0-9]{3,4}[а-яА-Яa-zA-Z]?)\b', trimmed)
            if m.group(1) not in ["2024", "2025", "2026", "2027", "2028"]
        ]
        if candidate_rooms:
            room = candidate_rooms[-1]

    # Clean Subject Name
    subject = trimmed
    for t in teachers:
        subject = subject.replace(t, " ")
    if url:
        subject = subject.replace(url, " ")

    # Remove week annotations
    subject = re.sub(r'(?:с\s+)?\b\d{1,2}\s*-\s*\d{1,2}\s*н\.?', ' ', subject, flags=re.I)
    subject = re.sub(r'\b\d{1,2}(?:\s*,\s*\d{1,2})+\s*н\.?', ' ', subject, flags=re.I)
    subject = re.sub(r'\b\d{1,2}\s*н\.?', ' ', subject, flags=re.I)

    # Remove room and aud
    if room:
        subject = re.sub(r'\b' + re.escape(room) + r'\b', ' ', subject)
    subject = re.sub(r'ауд\.?\s*', ' ', subject, flags=re.I)

    # Remove type tags
    subject = re.sub(r'\((?:л|пр|лаб|л\+пр|лек|практ)\)', ' ', subject, flags=re.I)

    # Remove building names from subject
    for b_kw in ["межлаука", "лево-булачная", "лицей им. н.и. лобачевского", "лицей", "1 к.-з.", "уникс"]:
        subject = re.sub(b_kw, ' ', subject, flags=re.I)

    # Remove subgroup indicators (1/2 гр., 1 гр, ч.н., н.н.)
    subject = re.sub(r'\b\d/\d\s*гр\.?', ' ', subject, flags=re.I)
    subject = re.sub(r'\b\d\s*гр\.?', ' ', subject, flags=re.I)
    subject = re.sub(r'\b[чн]\.[н\.]*', ' ', subject, flags=re.I)
    subject = re.sub(r'\b[чн]/[н\.]*', ' ', subject, flags=re.I)

    # Normalize whitespace & punctuation
    subject = re.sub(r'[,;\n\r\t]+', ' ', subject)
    subject = re.sub(r'\s+', ' ', subject).strip(' ,.-/()')

    if not subject or len(subject) < 2:
        return None

    teacher_str = ", ".join(teachers)

    return [{
        "subject": subject,
        "clean": trimmed,
        "teacher": teacher_str,
        "room": room,
        "building": building,
        "type": l_type,
        "url": url,
        "isAdditional": is_additional,
        "weekType": week_type,
        "weekStart": week_start,
        "weekEnd": week_end
    }]

def clean_major_and_note(raw: str) -> tuple:
    if not raw:
        return "", ""
    practice_note = ""
    practice_match = re.search(r'\(.*?(?:производственная\s+практика|практика).*?\)', raw, re.I)
    if practice_match:
        practice_note = practice_match.group(0).strip('() ')
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    first_line = lines[0] if lines else raw
    cutoff = re.search(r'(?i)\s+(?:[cс]\s+\d+|\d{1,2}[./]\d{1,2}|\d+(?:-\d+)?\s*н\b|\(\s*\d{1,2}[./]|\(\s*\d+(?:-\d+)?\s*н|\(.*практика)', first_line)
    if cutoff:
        major = first_line[:cutoff.start()]
    else:
        major = first_line
    major = re.sub(r'\(.*?\)', '', major)
    major = re.sub(r'\s+', ' ', major).strip(' ,;.-')
    if major:
        major = major[0].upper() + major[1:]
    return major, practice_note

def parse_schedule_xlsx(file_path, source_url):
    wb = openpyxl.load_workbook(file_path, data_only=True)
    result_groups = []
    lesson_counter = 0

    print(f"Loaded workbook. Sheets: {wb.sheetnames}")

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        s_low = sheet_name.lower()

        # Determine course label
        if "магистр" in s_low:
            if "1" in s_low or "перв" in s_low:
                course_name = "1 курс (магистратура)"
            else:
                course_name = "2 курс (магистратура)"
        elif "1" in s_low:
            course_name = "1 курс"
        elif "2" in s_low:
            course_name = "2 курс"
        elif "3" in s_low:
            course_name = "3 курс"
        elif "4" in s_low:
            course_name = "4 курс"
        elif "5" in s_low:
            course_name = "5 курс"
        elif "6" in s_low:
            course_name = "6 курс"
        else:
            course_name = sheet_name

        # 1. Expand merged cells
        merged_map = {}
        for rng in ws.merged_cells.ranges:
            top_val = ws.cell(rng.min_row, rng.min_col).value
            if top_val is not None:
                for r in range(rng.min_row, rng.max_row + 1):
                    for c in range(rng.min_col, rng.max_col + 1):
                        merged_map[(r, c)] = top_val

        def get_val(r, c):
            if (r, c) in merged_map:
                return str(merged_map[(r, c)] or "").strip()
            return str(ws.cell(r, c).value or "").strip()

        # 2. Locate header row with 'день' and 'время'
        day_col = None
        time_col = None
        header_row = None

        for r in range(1, min(12, ws.max_row + 1)):
            for c in range(1, min(10, ws.max_column + 1)):
                val = get_val(r, c).lower()
                if "день" in val and day_col is None:
                    day_col = c
                    header_row = r
                elif "время" in val and time_col is None:
                    time_col = c
                    if header_row is None:
                        header_row = r

        if not header_row or not day_col or not time_col:
            print(f"Skipping sheet {sheet_name}: header not found (h={header_row}, d={day_col}, t={time_col})")
            continue

        # 3. Locate groups in header_row
        from collections import Counter
        groups = []
        for c in range(max(day_col, time_col) + 1, ws.max_column + 1):
            g_val = get_val(header_row, c).strip()
            m = re.search(r"06-\s*(\d{3})", g_val)
            if m:
                clean_g = f"06-{m.group(1)}"
                raw_major = get_val(header_row + 1, c).strip()
                clean_m, p_note = clean_major_and_note(raw_major)

                # Check if group has subgroup in parens
                sub_match = re.search(r"\((\d+)\)", g_val)
                subgrp = sub_match.group(1) if sub_match else ""
                full_group_name = f"{clean_g} ({subgrp})" if subgrp else clean_g

                groups.append({
                    "col": c,
                    "group": full_group_name,
                    "shortGroup": clean_g,
                    "major": clean_m,
                    "course": course_name,
                    "specialization": "",
                    "practiceNote": p_note
                })

        # Disambiguate duplicate group numbers on the same sheet (e.g. Master's profiles)
        counts = Counter(g["group"] for g in groups)
        for g in groups:
            if counts[g["group"]] > 1:
                g["specialization"] = g["major"]
                g["group"] = f"{g['shortGroup']} ({g['major']})"
            g["id"] = g["group"]

        print(f"Sheet '{sheet_name}': detected {len(groups)} groups for course '{course_name}'")

        # 4. Parse grid
        cur_day_name = "понедельник"
        cur_day_idx = 1
        cur_time = "08:30-10:00"
        cur_start = "08:30"
        cur_end = "10:00"

        # Initialize days map keyed by column index to isolate groups with shared numbers
        group_days_map = {
            g["col"]: {di: {"name": dn, "idx": di, "lessons": []} for dn, di in DAYS_ORDER}
            for g in groups
        }
        seen_keys = set()

        for r in range(header_row + 2, ws.max_row + 1):
            d_val = get_val(r, day_col).lower()
            t_val = get_val(r, time_col)

            for dn, di in DAYS_ORDER:
                if dn in d_val:
                    cur_day_name = dn
                    cur_day_idx = di
                    break

            time_matches = re.findall(r"(\d{1,2})[.:](\d{2})", t_val)
            if len(time_matches) >= 2:
                h1, m1 = int(time_matches[0][0]), time_matches[0][1]
                h2, m2 = int(time_matches[1][0]), time_matches[1][1]
                cur_start = f"{h1:02d}:{m1}"
                cur_end = f"{h2:02d}:{m2}"
                cur_time = f"{cur_start}-{cur_end}"

            if not cur_day_name or not cur_time:
                continue

            for g in groups:
                cell_text = get_val(r, g["col"])
                if not cell_text or cell_text.lower() in ["день", "время", "понедельник", "вторник", "среда", "четверг", "пятница", "суббота"]:
                    continue

                chunks = split_cell_into_lesson_texts(cell_text)
                for chunk in chunks:
                    parsed_list = parse_lesson_text(chunk)
                    if not parsed_list:
                        continue

                    for p in parsed_list:
                        key = f"{g['col']}_{cur_day_idx}_{cur_time}_{p['subject']}_{p['weekStart']}_{p['weekEnd']}_{p['weekType']}_{p['teacher']}_{p['room']}"
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)

                        lesson_counter += 1
                        lesson = {
                            "id": f"{g['id']}-{lesson_counter}",
                            "subject": p["subject"],
                            "rawText": p["clean"],
                            "teacher": p["teacher"],
                            "room": p["room"],
                            "building": p["building"],
                            "type": p["type"],
                            "url": p["url"],
                            "isAdditional": p["isAdditional"],
                            "weekType": p["weekType"],
                            "weekStart": p["weekStart"],
                            "weekEnd": p["weekEnd"],
                            "time": cur_time,
                            "timeStart": cur_start,
                            "timeEnd": cur_end
                        }
                        group_days_map[g["col"]][cur_day_idx]["lessons"].append(lesson)

        # Assemble groups for this sheet
        for g in groups:
            days_list = []
            for dn, di in DAYS_ORDER:
                d = group_days_map[g["col"]][di]
                if d["lessons"]:
                    days_list.append({
                        "dayName": d["name"],
                        "dayIndex": d["idx"],
                        "lessons": d["lessons"]
                    })

            result_groups.append({
                "id": g["id"],
                "group": g["group"],
                "course": g["course"],
                "major": g["major"],
                "days": days_list,
                "shortGroup": g["shortGroup"],
                "specialization": g["specialization"],
                "practiceNote": g.get("practiceNote") or ""
            })

    iso_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": 4,
        "semester": compute_semester_string(),
        "updatedAt": iso_date,
        "sourceUrl": source_url,
        "groups": result_groups
    }

def main():
    latest_url = get_latest_xlsx_url()
    if not latest_url:
        print("Failed to find latest XLSX URL for Physics")
        sys.exit(1)

    print(f"Latest Physics XLSX URL: {latest_url}")
    local_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "physics_schedule_temp.xlsx")
    print("Downloading XLSX...")
    if not download_file(latest_url, local_file, HEADERS):
        print("Failed to download XLSX", file=sys.stderr)
        sys.exit(1)

    try:
        db = parse_schedule_xlsx(local_file, latest_url)
        save_database_with_cache_check(db, OUTPUT_FILE)
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)

if __name__ == "__main__":
    main()
