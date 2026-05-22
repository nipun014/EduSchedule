import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def extract_solution(data, x, solver):
    classes = data['classes']
    P = data['periods_per_day']
    subjects = data['subjects']
    teachers = data['teachers']

    out = {c: [] for c in classes}
    for c in classes:
        for p in range(P):
            entry = {'period': p+1, 'subject': None, 'teacher': None}
            for s in subjects:
                for t in teachers:
                    if s in data['teacher_info'][t]['can_teach']:
                        var = x[c][p][s].get(t)
                        if var is not None and solver.Value(var) == 1:
                            entry['subject'] = s
                            entry['teacher'] = t
            out[c].append(entry)
    return out


def export_solution_json(data, x, solver, output_path: str = None):
    if output_path is None:
        output_path = os.getenv('SOLUTION_JSON', 'solution.json')
    classes = data['classes']
    days = data['days']
    P = data['periods_per_day']
    subjects = data['subjects']
    teachers = data['teachers']
    rooms = data['rooms']

    solution = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "status": "feasible",
            "objective_value": float(solver.ObjectiveValue()),
            "solver": "Google OR-Tools CP-SAT",
            "days": days,
            "periods_per_day": P
        },
        "class_timetables": {},
        "teacher_timetables": {},
        "room_utilization": {}
    }

    # Class timetables
    for c in classes:
        timetable = []
        for d in range(days):
            day_schedule = []
            for p in range(P):
                period = {
                    "day": d + 1,
                    "period": p + 1,
                    "subject": None,
                    "teacher": None,
                    "room": None
                }
                found = False
                for s in subjects:
                    for t in teachers:
                        if s in data['teacher_info'][t]['can_teach']:
                            if t in x[c][d][p].get(s, {}):
                                for r in rooms:
                                    var = x[c][d][p][s][t].get(r)
                                    if var is not None and solver.Value(var) == 1:
                                        period['subject'] = s
                                        period['teacher'] = t
                                        period['room'] = r
                                        found = True
                                        break
                            if found:
                                break
                    if found:
                        break
                day_schedule.append(period)
            timetable.append(day_schedule)
        solution["class_timetables"][c] = timetable

    # Teacher timetables
    for t in teachers:
        timetable = []
        for d in range(days):
            day_schedule = []
            for p in range(P):
                period = {
                    "day": d + 1,
                    "period": p + 1,
                    "class": None,
                    "subject": None,
                    "room": None
                }
                found = False
                for c in classes:
                    for s in subjects:
                        if s in data['teacher_info'][t]['can_teach']:
                            if t in x[c][d][p].get(s, {}):
                                for r in rooms:
                                    var = x[c][d][p][s][t].get(r)
                                    if var is not None and solver.Value(var) == 1:
                                        period['class'] = c
                                        period['subject'] = s
                                        period['room'] = r
                                        found = True
                                        break
                            if found:
                                break
                    if found:
                        break
                day_schedule.append(period)
            timetable.append(day_schedule)
        solution["teacher_timetables"][t] = timetable

    # Room utilization
    for r in rooms:
        utilization = []
        for d in range(days):
            day_usage = []
            for p in range(P):
                slot = {
                    "day": d + 1,
                    "period": p + 1,
                    "class": None,
                    "subject": None,
                    "teacher": None
                }
                found = False
                for c in classes:
                    for s in subjects:
                        for t in teachers:
                            if s in data['teacher_info'][t]['can_teach']:
                                if t in x[c][d][p].get(s, {}):
                                    var = x[c][d][p][s][t].get(r)
                                    if var is not None and solver.Value(var) == 1:
                                        slot['class'] = c
                                        slot['subject'] = s
                                        slot['teacher'] = t
                                        found = True
                                        break
                            if found:
                                break
                    if found:
                        break
                day_usage.append(slot)
            utilization.append(day_usage)
        solution["room_utilization"][r] = utilization

    with open(output_path, 'w') as f:
        json.dump(solution, f, indent=2)
    
    print(f"Saved solution to {output_path}")
    return solution
