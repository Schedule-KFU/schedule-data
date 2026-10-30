import sys
import json
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
    semester = "1 семестр 2026/2027"

    for file_name, label in INSTITUTES:
        path = base_dir / file_name
        if not path.exists():
            print(f"Warning: {path} not found, skipping {label}.")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        groups = data.get("groups", [])
        all_groups.extend(groups)
        stats.append(f"{len(groups)} {label}")
        if data.get("semester"):
            semester = data["semester"]

    if not all_groups:
        print("Error: No groups found from any institute.", file=sys.stderr)
        return False

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
        try:
            with open(combined_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            if (existing_data.get("groups") == all_groups and
                existing_data.get("semester") == semester):
                combined_data["updatedAt"] = existing_data.get("updatedAt", iso_now)
                print(f"✅ Combined schedule content is identical. Preserving updatedAt timestamp ({combined_data['updatedAt']}).")
        except Exception as e:
            print(f"Warning: Failed to compare with existing {combined_path}: {e}")

    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved schedule_combined.json: {len(all_groups)} groups ({' + '.join(stats)})")
    return True

if __name__ == "__main__":
    merge_schedules()

