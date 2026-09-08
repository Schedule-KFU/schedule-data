import sys
import os
import re
import json
from datetime import datetime, timezone
import requests
import openpyxl

KFU_URL = "https://kpfu.ru/computing-technology/raspisanie"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_latest_xlsx_url():
    resp = requests.get(KFU_URL, headers=HEADERS, timeout=20)
    resp.encoding = resp.apparent_encoding
    html = resp.text

    pattern = r'href=["\'](https?://kpfu\.ru/portal/docs/[^"\']*?\.xlsx)["\']'
    matches = re.findall(pattern, html, flags=re.IGNORECASE)
    
    for m in matches:
        if "raspisanie" in m.lower():
            return m
    if matches:
        return matches[0]
    return None

def compute_semester_string():
    now = datetime.now()
    month = now.month
    year = now.year
    is_autumn = month >= 9 or month <= 1
    sem_num = 1 if is_autumn else 2
    acad_start = year if is_autumn else year - 1
    acad_end = acad_start + 1
    return f"{sem_num} семестр {acad_start}/{acad_end}"

def split_cell_into_lesson_texts(text):
    trimmed = text.strip()
    if not trimmed:
        return []
    split_pattern = r"(?:;\s*(?=\()|\n\s*(?=\()|(?<=[\.\)])\s+(?=\((?:[нч]/н|[0-9]{1,2}\s*-\s*[0-9]{1,2})))"
    parts = re.split(split_pattern, trimmed, flags=re.IGNORECASE)
    res = [p.strip() for p in parts if p.strip()]
    return res if res else [trimmed]

def parse_lesson_text(txt):
    trimmed = txt.strip()
    if not trimmed:
        return None
    
    lower = trimmed.lower()
    # Reject footers and signatures
    if "____" in trimmed or \
       "департамент образования" in lower or \
       "учебно-методическ" in lower or \
       "утверждаю" in lower or \
       "согласовано" in lower or \
       "яббаров" in lower or \
       ("ивмиит" in lower and "хафизова" in lower):
        return None

    week_type = "all"
    week_start = 1
    week_end = 18

    range_pattern = r"\(\s*(?:с\s+)?(?:([нч]/н)\s*)?([0-9]{1,2})\s*-+\s*([0-9]{1,2})\s*(?:нед|недел|лаб|лек|пр|\))"
    parity_match = re.search(range_pattern, trimmed, flags=re.IGNORECASE)
    if parity_match:
        tag = parity_match.group(1)
        if tag:
            tag_low = tag.lower()
            if "н/н" in tag_low:
                week_type = "odd"
            elif "ч/н" in tag_low:
                week_type = "even"
        
        start_str = parity_match.group(2)
        end_str = parity_match.group(3)
        if start_str and end_str:
            week_start = int(start_str)
            week_end = int(end_str)
            if week_type == "all":
                if week_start == 1 and week_end == 9:
                    week_type = "first_half"
                elif week_start == 10 and week_end == 18:
                    week_type = "second_half"
    elif re.search(r"\bн/н\b|\(н/н\)", trimmed, flags=re.IGNORECASE):
        week_type = "odd"
    elif re.search(r"\bч/н\b|\(ч/н\)", trimmed, flags=re.IGNORECASE):
        week_type = "even"

    clean = re.sub(r"^\s*\(\s*(?:с\s+)?[^\)]*(?:нед|недел|[нч]/н)[^\)]*\)\s*", "", trimmed, flags=re.IGNORECASE).strip()

    room = ""
    building = ""

    sub_cleans = [s.strip() for s in clean.split(";") if s.strip()]
    subgroups = []
    
    teacher_pattern = r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.?"

    for sub in sub_cleans:
        building = ""
        room = ""

        # 1. Building
        kreml_match = re.search(r"(?:\(\s*)?[Кк]р(?:ем|ме)[л\.]*\s*(\d+[\s\-]*(?:[А-Яа-яA-Za-z])?)\)?", sub, flags=re.IGNORECASE)
        spartak_match = re.search(r"(?:\(\s*)?[Сс]партаковская\s*(\d+[\s\-]*(?:[А-Яа-яA-Za-z])?)\)?", sub, flags=re.IGNORECASE)

        if kreml_match:
            num = kreml_match.group(1).replace(" ", "").replace("-", "").upper()
            building = f"Кремл. {num}"
        elif spartak_match:
            num = spartak_match.group(1).replace(" ", "").replace("-", "").upper()
            building = f"Спартаковская {num}"
        elif "уникс" in sub.lower() or "нужина" in sub.lower():
            building = "УНИКС"

        # 2. Room
        room_pattern = r"(?:ауд\.?\s*)+(.*?)(?=\s*(?:\(?\s*[Кк]р(?:ем|ме)[л\.]*|\(?\s*[Сс]партаковская|\(?\s*УНИКС|\(?\s*[Нн]ужина|\s*\-\s*д\.|\s*\-\s*лек\.|\s*\-\s*лаб\.|\s*\-\s*пр\.|\;|\)|$))"
        r_match = re.search(room_pattern, sub, flags=re.IGNORECASE)
        if r_match:
            r_str = r_match.group(1).strip(" ,.-;()\\t\\n")
            if r_str:
                room = r_str

        if not room and building:
            f_match = re.search(r"(\d{3,4}[А-Яа-яA-Za-z]?)\s*\(?", sub)
            if f_match:
                room = f_match.group(1).strip()
        elif not room and "уникс" in sub.lower():
            room = "спорткомплекс"

        # 3. Teachers
        teachers = re.findall(teacher_pattern, sub)
        room_list = [r.strip() for r in re.split(r'[,/]', room) if r.strip()] if room else []

        if len(teachers) > 1 and len(room_list) > 1 and len(teachers) == len(room_list):
            for t, r in zip(teachers, room_list):
                subgroups.append({
                    "teacher": t,
                    "room": r,
                    "building": building
                })
        else:
            teacher_str = ", ".join(teachers)
            subgroups.append({
                "teacher": teacher_str,
                "room": room,
                "building": building
            })

    # If there are multiple subgroups, filter out completely empty ones
    if len(subgroups) > 1:
        subgroups = [sg for sg in subgroups if sg["teacher"] or sg["room"]]
    if not subgroups:
        subgroups = [{"teacher": "", "room": "", "building": ""}]

    # 4. Lesson Type
    clean_low = clean.lower()
    is_additional = bool(re.search(r"\s*-\s*д\.?(?:\s|$)", clean_low))

    if "лаб." in clean_low or "лаборатор" in clean_low:
        l_type = "lab"
    elif "дистанцион" in clean_low:
        l_type = "distance"
    elif "эор" in clean_low:
        l_type = "eor"
    elif "практи" in clean_low or "пр." in clean_low:
        l_type = "practice"
    elif "лек." in clean_low or "лекция" in clean_low:
        l_type = "lecture"
    else:
        l_type = "other"

    # 5. Subject
    subject = clean
    room_rx = re.search(r"(?:ауд\.?|[0-9]{3,4}\s*\(?Кремл)", clean, flags=re.IGNORECASE)
    if room_rx:
        subject = subject[:room_rx.start()]
    
    for bp in ["шахматный центр", "кск кфу"]:
        idx = subject.lower().find(bp)
        if idx != -1:
            subject = subject[:idx]
    
    all_teachers = re.findall(teacher_pattern, clean)
    for t in all_teachers:
        subject = subject.replace(t, "")
    
    subject = re.sub(r"\s*-\s*д\.?(?:\s|$)", "", subject, flags=re.IGNORECASE)
    subject = subject.split(";")[0]
    subject = subject.strip(" ,.-;()\\t\\n")
    subject = re.sub(r"\s+", " ", subject)

    # 6. Custom time (PE)
    custom_time = None
    time_rx = re.search(r"(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})", trimmed)
    if time_rx:
        low_trimmed = trimmed.lower()
        if "проводится" in low_trimmed or "спорт" in low_trimmed or "физическ" in low_trimmed or "уникс" in low_trimmed:
            h1 = int(time_rx.group(1))
            m1 = time_rx.group(2)
            h2 = int(time_rx.group(3))
            m2 = time_rx.group(4)
            if 7 <= h1 <= 21 and 7 <= h2 <= 22:
                custom_time = {
                    "start": f"{h1:02d}:{m1}",
                    "end": f"{h2:02d}:{m2}"
                }

    results = []
    for sg in subgroups:
        results.append({
            "subject": subject,
            "clean": clean,
            "teacher": sg["teacher"],
            "room": sg["room"],
            "building": sg["building"],
            "type": l_type,
            "isAdditional": is_additional,
            "weekType": week_type,
            "weekStart": week_start,
            "weekEnd": week_end,
            "customTime": custom_time
        })

    return results

def parse_schedule_xlsx(file_path, source_url):
    print("Loading workbook...")
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active

    # Fast cell getter resolving merged ranges
    merged_dict = {}
    for mr in sheet.merged_cells.ranges:
        val = sheet.cell(row=mr.min_row, column=mr.min_col).value
        if val is not None:
            s_val = str(val).strip()
            if s_val:
                for r in range(mr.min_row, mr.max_row + 1):
                    for c in range(mr.min_col, mr.max_col + 1):
                        merged_dict[(r, c)] = s_val

    def get_cell_val(row, col):
        if (row, col) in merged_dict:
            return merged_dict[(row, col)]
        v = sheet.cell(row=row, column=col).value
        return str(v).strip() if v is not None else ""

    max_col = sheet.max_column
    start_col = 5  # Column 'E'

    groups = []
    cur_course = "1 курс"
    cur_major = ""

    print("Scanning groups...")
    for ci in range(start_col, max_col + 1):
        r17 = get_cell_val(17, ci)
        r17_low = r17.lower()
        if "магистратура" in r17_low:
            if "1" in r17_low or "первый" in r17_low:
                cur_course = "1 курс (магистратура)"
            elif "2" in r17_low or "второй" in r17_low:
                cur_course = "2 курс (магистратура)"
            else:
                cur_course = "Магистратура"
        elif "курс" in r17_low:
            cur_course = r17.strip()
        elif r17:
            cur_major = r17.strip()

        g_name = get_cell_val(18, ci)
        if g_name and "курс" not in g_name.lower() and re.search(r'(?:\d{2}-)?\d{3}', g_name):
            final_name = g_name.strip()
            if not final_name.startswith("09-"):
                final_name = f"09-{final_name}"

            course_name = cur_course
            if ".04." in cur_major or "магистр" in cur_major.lower():
                if "09-6" in final_name:
                    course_name = "1 курс (магистратура)"
                elif "09-5" in final_name:
                    course_name = "2 курс (магистратура)"
                else:
                    course_name = "Магистратура"

            groups.append({
                "colIdx": ci,
                "course": course_name,
                "major": cur_major,
                "group": final_name
            })

    print(f"Detected {len(groups)} groups.")

    days_order = [
        ("понедельник", 1), ("вторник", 2), ("среда", 3),
        ("четверг", 4), ("пятница", 5), ("суббота", 6)
    ]

    row_meta = {}
    cur_day_name = "понедельник"
    cur_day_idx = 1
    cur_time = "08:30-10:00"
    cur_start = "08:30"
    cur_end = "10:00"

    for ri in range(19, min(sheet.max_row + 1, 116)):
        c_val = get_cell_val(ri, 3).lower() # Column C
        d_val = get_cell_val(ri, 4)         # Column D

        for dn, di in days_order:
            if dn in c_val:
                cur_day_name = dn
                cur_day_idx = di
                break

        time_matches = re.findall(r"(\d{1,2})[.:](\d{2})", d_val)
        if len(time_matches) >= 2:
            h1 = int(time_matches[0][0])
            m1 = time_matches[0][1]
            h2 = int(time_matches[1][0])
            m2 = time_matches[1][1]
            cur_start = f"{h1:02d}:{m1}"
            cur_end = f"{h2:02d}:{m2}"
            cur_time = f"{cur_start}-{cur_end}"

        row_meta[ri] = {
            "dayName": cur_day_name,
            "dayIdx": cur_day_idx,
            "timeSlot": cur_time,
            "start": cur_start,
            "end": cur_end
        }

    result_groups = []
    lesson_counter = 0

    print("Parsing schedule grid...")
    for g in groups:
        ci = g["colIdx"]
        days_map = {di: {"name": dn, "idx": di, "lessons": []} for dn, di in days_order}
        seen = set()

        for ri in range(19, min(sheet.max_row + 1, 116)):
            val = get_cell_val(ri, ci)
            if not val:
                continue
            if val.lower() in ["вт", "ср", "чт", "пт", "сб", "вск"]:
                continue

            lesson_chunks = split_cell_into_lesson_texts(val)
            for chunk in lesson_chunks:
                parsed_list = parse_lesson_text(chunk)
                if not parsed_list:
                    continue
                for parsed in parsed_list:
                    meta = row_meta.get(ri)
                    if not meta:
                        continue

                    key = f"{meta['dayIdx']}_{meta['timeSlot']}_{parsed['clean']}_{parsed['weekStart']}_{parsed['weekEnd']}_{parsed['weekType']}_{parsed['teacher']}_{parsed['room']}"
                    if key in seen:
                        continue
                    seen.add(key)

                    lesson_counter += 1
                    start_slot = parsed["customTime"]["start"] if parsed["customTime"] else meta["start"]
                    end_slot = parsed["customTime"]["end"] if parsed["customTime"] else meta["end"]
                    time_slot = f"{start_slot}-{end_slot}" if parsed["customTime"] else meta["timeSlot"]

                    lesson = {
                        "id": f"{g['group']}-{lesson_counter}",
                        "subject": parsed["subject"],
                        "rawText": parsed["clean"],
                        "teacher": parsed["teacher"],
                        "room": parsed["room"],
                        "building": parsed["building"],
                        "type": parsed["type"],
                        "isAdditional": parsed["isAdditional"],
                        "weekType": parsed["weekType"],
                        "weekStart": parsed["weekStart"],
                        "weekEnd": parsed["weekEnd"],
                        "time": time_slot,
                        "timeStart": start_slot,
                        "timeEnd": end_slot
                    }
                    days_map[meta["dayIdx"]]["lessons"].append(lesson)

        days_list = []
        for dn, di in days_order:
            d = days_map[di]
            if d["lessons"]:
                days_list.append({
                    "dayName": d["name"],
                    "dayIndex": d["idx"],
                    "lessons": d["lessons"]
                })

        short_name = g["group"]
        spec = ""
        m = re.match(r"^(\d{2}-\d{3})\s*\((.*?)\)\s*\((\d+)\)$", g["group"])
        if m:
            short_name = f"{m.group(1)} ({m.group(3)})"
            spec = m.group(2)

        result_groups.append({
            "id": g["group"],
            "group": g["group"],
            "course": g["course"],
            "major": g["major"],
            "days": days_list,
            "shortGroup": short_name,
            "specialization": spec
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
        print("Failed to find latest XLSX URL")
        sys.exit(1)
    
    print(f"Latest XLSX URL: {latest_url}")
    local_file = "schedule.xlsx"
    print("Downloading XLSX...")
    r = requests.get(latest_url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    with open(local_file, "wb") as f:
        f.write(r.content)
    
    try:
        db = parse_schedule_xlsx(local_file, latest_url)
        out_file = "schedule.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        
        print(f"Success! Saved to {out_file}")
        print(f"Groups parsed: {len(db['groups'])}")
        total_lessons = sum(len(d['lessons']) for g in db['groups'] for d in g['days'])
        print(f"Total lessons parsed: {total_lessons}")
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)

if __name__ == "__main__":
    main()
