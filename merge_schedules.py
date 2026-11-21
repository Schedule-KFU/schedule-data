import sys
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from base_parser import compute_semester_meta

INSTITUTES = [
    ("schedule.json", "IVMIIT"),
    ("schedule_physics.json", "Physics"),
    ("schedule_ifmib.json", "IFMiB"),
]

def merge_schedules():
    base_dir = Path(__file__).parent
    combined_path = base_dir / "schedule_combined.json"

    all_groups = []
    stats = []
    semester = None

    for file_name, label in INSTITUTES:
        path = base_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Required {label} schedule not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        groups = data.get("groups", [])
        lessons = sum(len(day.get("lessons", [])) for group in groups for day in group.get("days", []))
        if not groups or not lessons:
            raise ValueError(f"{label} schedule contains no groups or lessons: {path}")
        source_semester = data.get("semester")
        if not source_semester or (semester and source_semester != semester):
            raise ValueError(f"Missing or inconsistent semester in {path}: {source_semester!r}")
        semester = source_semester
        all_groups.extend(groups)
        stats.append(f"{len(groups)} {label}")

    if not all_groups:
        print("Error: No groups found from any institute.", file=sys.stderr)
        raise ValueError("No groups found from any institute")

    # Sort groups by group display name
    all_groups.sort(key=lambda g: g.get("group", ""))

    iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    combined_data = {
        "version": 4,
        "schemaVersion": "1.0",
        "semester": semester,
        "semesterMeta": compute_semester_meta(),
        "updatedAt": iso_now,
        "sourceUrl": "https://kpfu.ru",
        "groups": all_groups
    }

    if combined_path.exists():
        with open(combined_path, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
        old_groups = existing_data.get("groups", [])
        old_lessons = sum(len(day.get("lessons", [])) for group in old_groups for day in group.get("days", []))
        new_lessons = sum(len(day.get("lessons", [])) for group in all_groups for day in group.get("days", []))
        if len(all_groups) < len(old_groups) * 0.7 or new_lessons < old_lessons * 0.7:
            raise ValueError(f"Combined schedule shrank: groups {len(old_groups)} -> {len(all_groups)}, lessons {old_lessons} -> {new_lessons}")
        if {k: v for k, v in existing_data.items() if k != "updatedAt"} == {k: v for k, v in combined_data.items() if k != "updatedAt"}:
            combined_data["updatedAt"] = existing_data.get("updatedAt", iso_now)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=base_dir, delete=False) as f:
            temporary_path = f.name
            json.dump(combined_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary_path, combined_path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)

    print(f"✅ Saved schedule_combined.json: {len(all_groups)} groups ({' + '.join(stats)})")
    return True

if __name__ == "__main__":
    merge_schedules()

