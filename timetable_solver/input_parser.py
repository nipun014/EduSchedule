from __future__ import annotations

import json
from typing import Any, Dict, List


def parse_text(text: str) -> Dict[str, Any]:
    """Parse input text into a raw dict.

    Tries JSON first, then YAML (if available). Raises a ValueError if parsing fails.
    """
    text = text.strip()
    if not text:
        raise ValueError("Empty input")

    # Try JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try YAML (optional dependency)
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    raise ValueError("Unable to parse input as JSON or YAML.")


def _subjects_to_dict(subjects: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(subjects, dict):
        return subjects
    if isinstance(subjects, list):
        out: Dict[str, Dict[str, Any]] = {}
        for item in subjects:
            if isinstance(item, str):
                out[item] = {
                    "hours_per_week": 1,
                    "room_type": "standard",
                }
            elif isinstance(item, dict):
                name = item.get("name") or item.get("id") or item.get("subject")
                if not name:
                    raise ValueError("Subject items must include a 'name' field or be strings.")
                props = {k: v for k, v in item.items() if k not in ("name", "id", "subject")}
                props.setdefault("hours_per_week", 1)
                props.setdefault("room_type", "standard")
                props.setdefault("is_heavy", False)
                props.setdefault("is_double_period", False)
                out[name] = props
            else:
                raise ValueError("Unsupported subject entry type.")
        return out
    raise ValueError("'subjects' must be a dict or a list.")


def _rooms_to_dict(rooms: Any) -> Dict[str, Dict[str, Any]]:
    if rooms is None:
        return {}
    if isinstance(rooms, dict):
        return rooms
    if isinstance(rooms, list):
        out: Dict[str, Dict[str, Any]] = {}
        for item in rooms:
            if isinstance(item, str):
                out[item] = {"type": "standard"}
            elif isinstance(item, dict):
                name = item.get("name") or item.get("id") or item.get("room")
                if not name:
                    raise ValueError("Room items must include a 'name' field or be strings.")
                props = {k: v for k, v in item.items() if k not in ("name", "id", "room")}
                props.setdefault("type", "standard")
                out[name] = props
            else:
                raise ValueError("Unsupported room entry type.")
        return out
    raise ValueError("'rooms' must be a dict, list or omitted.")


def _teachers_to_dict(teachers: Any, *, days: int, periods_per_day: int) -> Dict[str, Dict[str, Any]]:
    def default_availability() -> List[List[int]]:
        return [[1 for _ in range(periods_per_day)] for _ in range(days)]

    if isinstance(teachers, dict):
        # Ensure defaults
        for t, info in teachers.items():
            info.setdefault("can_teach", [])
            info.setdefault("availability", default_availability())
        return teachers
    if isinstance(teachers, list):
        out: Dict[str, Dict[str, Any]] = {}
        for item in teachers:
            if isinstance(item, str):
                out[item] = {
                    "can_teach": [],
                    "availability": default_availability(),
                }
            elif isinstance(item, dict):
                name = item.get("name") or item.get("id") or item.get("teacher")
                if not name:
                    raise ValueError("Teacher items must include a 'name' field or be strings.")
                props = {k: v for k, v in item.items() if k not in ("name", "id", "teacher")}
                props.setdefault("can_teach", [])
                props.setdefault("availability", default_availability())
                out[name] = props
            else:
                raise ValueError("Unsupported teacher entry type.")
        return out
    raise ValueError("'teachers' must be a dict or a list.")


def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw dict into the structure expected by the solver/model.

    Required keys (directly or after normalization):
      - classes: list[str]
      - subjects: dict[name->props] or list
      - teachers: dict[name->props] or list

    Optional:
      - rooms
      - class_subjects
      - days (default 5)
      - periods_per_day (default 6)
    """
    if "classes" not in raw:
        raise ValueError("Missing required key: 'classes'")
    if "subjects" not in raw:
        raise ValueError("Missing required key: 'subjects'")
    if "teachers" not in raw:
        raise ValueError("Missing required key: 'teachers'")

    days = int(raw.get("days", 5))
    periods_per_day = int(raw.get("periods_per_day", 6))

    classes = list(raw["classes"])  # ensure list
    subject_info = _subjects_to_dict(raw["subjects"])
    room_info = _rooms_to_dict(raw.get("rooms"))
    teacher_info = _teachers_to_dict(raw["teachers"], days=days, periods_per_day=periods_per_day)

    subjects = list(subject_info.keys())
    teachers = list(teacher_info.keys())
    rooms = list(room_info.keys())

    class_subjects = raw.get("class_subjects")
    if not isinstance(class_subjects, dict):
        class_subjects = {c: subjects for c in classes}

    return {
        "classes": classes,
        "days": days,
        "periods_per_day": periods_per_day,
        "subjects": subjects,
        "teachers": teachers,
        "rooms": rooms,
        "teacher_info": teacher_info,
        "room_info": room_info,
        "subject_info": subject_info,
        "class_subjects": class_subjects,
        "raw": raw,
    }
