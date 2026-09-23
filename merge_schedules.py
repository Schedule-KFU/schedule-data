import json
from datetime import datetime, timezone
from pathlib import Path

def merge_schedules():
    base_dir = Path(__file__).parent
    ivmiit_path = base_dir / "schedule.json"
    physics_path = base_dir / "schedule_physics.json"
    combined_path = base_dir / "schedule_combined.json"

    if not ivmiit_path.exists():
        print(f"Error: {ivmiit_path} not found.")
        return False
    if not physics_path.exists():
        print(f"Error: {physics_path} not found.")
        return False

    with open(ivmiit_path, "r", encoding="utf-8") as f:
        ivmiit_data = json.load(f)

    with open(physics_path, "r", encoding="utf-8") as f:
        physics_data = json.load(f)

    ivmiit_groups = ivmiit_data.get("groups", [])
    physics_groups = physics_data.get("groups", [])
    all_groups = ivmiit_groups + physics_groups

    # Sort groups by group display name
    all_groups.sort(key=lambda g: g.get("group", ""))

    iso_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    combined_data = {
        "version": 4,
        "semester": ivmiit_data.get("semester") or physics_data.get("semester") or "1 семестр 2026/2027",
        "updatedAt": iso_now,
        "sourceUrl": "https://kpfu.ru",
        "groups": all_groups
    }

    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Generated schedule_combined.json: {len(all_groups)} groups ({len(ivmiit_groups)} IVMIIT + {len(physics_groups)} Physics)")
    return True

if __name__ == "__main__":
    merge_schedules()
