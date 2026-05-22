from pathlib import Path
import json
from typing import Dict, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATA_FILE = Path(__file__).parent / os.getenv('DATA_FILE', 'sample_data.json')


def load_data(path: Path = DATA_FILE) -> Dict:
    with open(path, 'r') as f:
        data = json.load(f)
    classes = data['classes']
    days = data.get('days', 5)
    periods_per_day = data.get('periods_per_day', 6)
    subjects = list(data['subjects'].keys())
    teachers = list(data['teachers'].keys())
    rooms = list(data.get('rooms', {}).keys())

    teacher_info = data['teachers']
    room_info = data.get('rooms', {})
    subject_info = data['subjects']
    class_subjects = data.get('class_subjects', {c: subjects for c in classes})

    return {
        'classes': classes,
        'days': days,
        'periods_per_day': periods_per_day,
        'subjects': subjects,
        'teachers': teachers,
        'rooms': rooms,
        'teacher_info': teacher_info,
        'room_info': room_info,
        'subject_info': subject_info,
        'class_subjects': class_subjects,
        'raw': data
    }
