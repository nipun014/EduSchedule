import io
import json
from collections import defaultdict
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Timetable Manager", layout="wide")


# -----------------------------
# Parsing / validation
# -----------------------------
def parse_uploaded_json(uploaded_file) -> dict | None:
    if not uploaded_file:
        return None
    try:
        data = json.load(uploaded_file)
    except Exception as ex:
        st.error(f"Could not parse JSON: {ex}")
        return None

    required = [
        "days",
        "periods_per_day",
        "classes",
        "subjects",
        "teachers",
        "class_subjects",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        st.error(f"Invalid JSON: missing keys -> {', '.join(missing)}")
        return None

    return data


def get_day_labels(days_count: int) -> list[str]:
    base = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if days_count <= len(base):
        return base[:days_count]
    return [f"Day {i+1}" for i in range(days_count)]


def get_period_labels(periods_per_day: int) -> list[str]:
    return [f"Period {i+1}" for i in range(periods_per_day)]


# -----------------------------
# Timetable generator (greedy)
# -----------------------------
def generate_schedule(data: dict) -> dict:
    """
    Generates a global schedule:
      schedule[class_name][(day_idx, period_idx)] = {subject, teacher, room, conflict}
    """
    classes = data["classes"]
    subjects = data["subjects"]
    teachers = data["teachers"]
    class_subjects = data["class_subjects"]
    rooms = data.get("rooms", {})

    days = int(data["days"])
    periods = int(data["periods_per_day"])

    # subject -> list of teachers who can teach it
    teachers_by_subject = defaultdict(list)
    for tid, tinfo in teachers.items():
        for s in tinfo.get("can_teach", []):
            teachers_by_subject[s].append(tid)

    # room type -> list of room ids
    rooms_by_type = defaultdict(list)
    for rid, rinfo in rooms.items():
        rooms_by_type[rinfo.get("type", "standard")].append(rid)

    # Remaining hours per class-subject
    remaining = {}
    for cls in classes:
        remaining[cls] = {}
        for sub in class_subjects.get(cls, []):
            remaining[cls][sub] = int(subjects.get(sub, {}).get("hours_per_week", 0))

    # Occupancy trackers
    teacher_busy = defaultdict(set)  # (d,p) -> {teacher_id}
    room_busy = defaultdict(set)  # (d,p) -> {room_id}

    schedule = {cls: {} for cls in classes}
    conflicts = 0

    for d in range(days):
        for p in range(periods):
            for cls in classes:
                # candidate subjects with remaining hours
                candidates = [s for s, hrs in remaining[cls].items() if hrs > 0]

                if not candidates:
                    schedule[cls][(d, p)] = {
                        "subject": "Free",
                        "teacher": "-",
                        "room": "-",
                        "conflict": False,
                    }
                    continue

                # choose subject with highest remaining load first
                candidates.sort(key=lambda s: remaining[cls][s], reverse=True)

                assigned = False
                for sub in candidates:
                    allowed_teachers = teachers_by_subject.get(sub, [])
                    room_type = subjects.get(sub, {}).get("room_type", "standard")
                    possible_rooms = rooms_by_type.get(room_type, []) or rooms_by_type.get("standard", [])

                    # teacher selection (available + not busy)
                    selected_teacher = None
                    for tid in allowed_teachers:
                        availability = teachers.get(tid, {}).get("availability", [])
                        is_available = (
                            d < len(availability)
                            and p < len(availability[d])
                            and availability[d][p] == 1
                        )
                        if is_available and tid not in teacher_busy[(d, p)]:
                            selected_teacher = tid
                            break

                    if not selected_teacher:
                        continue

                    # room selection (not busy)
                    selected_room = "-"
                    if possible_rooms:
                        free_room = next((r for r in possible_rooms if r not in room_busy[(d, p)]), None)
                        if free_room:
                            selected_room = free_room
                        else:
                            # no free room of required type at this slot
                            continue

                    # assign
                    schedule[cls][(d, p)] = {
                        "subject": sub,
                        "teacher": selected_teacher,
                        "room": selected_room,
                        "conflict": False,
                    }
                    remaining[cls][sub] -= 1
                    teacher_busy[(d, p)].add(selected_teacher)
                    if selected_room != "-":
                        room_busy[(d, p)].add(selected_room)
                    assigned = True
                    break

                if not assigned:
                    # unresolved slot
                    schedule[cls][(d, p)] = {
                        "subject": "Unassigned",
                        "teacher": "N/A",
                        "room": "N/A",
                        "conflict": True,
                    }
                    conflicts += 1

    return {"schedule": schedule, "conflicts": conflicts, "days": days, "periods": periods}


def build_class_dataframe(gen_result: dict, class_name: str) -> pd.DataFrame:
    day_labels = get_day_labels(gen_result["days"])
    period_labels = get_period_labels(gen_result["periods"])

    df = pd.DataFrame("", index=period_labels, columns=day_labels)

    for d in range(gen_result["days"]):
        for p in range(gen_result["periods"]):
            item = gen_result["schedule"][class_name][(d, p)]
            cell = f'{item["subject"]}\n{item["teacher"]}\n{item["room"]}'
            if item["conflict"]:
                cell += "  ⚠ Conflict"
            df.iloc[p, d] = cell

    return df


def conflict_style(value: str) -> str:
    if isinstance(value, str) and "⚠ Conflict" in value:
        return "background-color:#ffe5e5;color:#8b0000;font-weight:700;"
    return ""


# -----------------------------
# Export helpers
# -----------------------------
def build_export_dataframe(gen_result: dict, class_name: str | None = None) -> pd.DataFrame:
    rows = []
    classes = [class_name] if class_name else list(gen_result["schedule"].keys())

    day_labels = get_day_labels(gen_result["days"])
    period_labels = get_period_labels(gen_result["periods"])

    for cls in classes:
        for (d, p), item in gen_result["schedule"][cls].items():
            rows.append(
                {
                    "Class": cls,
                    "DayIndex": d + 1,
                    "PeriodIndex": p + 1,
                    "Day": day_labels[d],
                    "Period": period_labels[p],
                    "Subject": item.get("subject", ""),
                    "Teacher": item.get("teacher", ""),
                    "Room": item.get("room", ""),
                    "Conflict": bool(item.get("conflict", False)),
                }
            )

    df = pd.DataFrame(rows)
    return df.sort_values(["Class", "DayIndex", "PeriodIndex"]).reset_index(drop=True)


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes | None:
    buffer = io.BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Timetable", index=False)
        buffer.seek(0)
        return buffer.read()
    except Exception:
        return None


def dataframe_to_pdf_bytes(df: pd.DataFrame, title: str = "Timetable Export") -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfgen import canvas
    except Exception:
        return None

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    _, height = landscape(A4)

    y = height - 30
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, y, title)
    y -= 20
    c.setFont("Helvetica", 8)

    headers = ["Class", "Day", "Period", "Subject", "Teacher", "Room", "Conflict"]
    c.drawString(30, y, " | ".join(headers))
    y -= 12

    for _, r in df.iterrows():
        line = f'{r["Class"]} | {r["Day"]} | {r["Period"]} | {r["Subject"]} | {r["Teacher"]} | {r["Room"]} | {r["Conflict"]}'
        c.drawString(30, y, line[:170])
        y -= 11
        if y < 30:
            c.showPage()
            y = height - 30
            c.setFont("Helvetica", 8)

    c.save()
    buffer.seek(0)
    return buffer.read()


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Timetable", "Constraints", "Export"])

st.sidebar.subheader("Input JSON")
uploaded_json = st.sidebar.file_uploader("Upload competitive JSON", type=["json"])
parsed = parse_uploaded_json(uploaded_json)
if parsed:
    st.session_state["input_data"] = parsed
data = st.session_state.get("input_data")


# -----------------------------
# Pages
# -----------------------------
def render_dashboard():
    st.title("Timetable Manager")
    st.caption("Upload competitive-format JSON and generate timetable.")

    if not data:
        st.warning("Please upload your JSON file from the sidebar.")
        return

    total_teachers = len(data.get("teachers", {}))
    total_classes = len(data.get("classes", []))
    total_constraints = len(data.get("weights", {})) + 3

    generated = st.session_state.get("generated_result")
    conflicts = generated["conflicts"] if generated else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Teachers", total_teachers)
    c2.metric("Total Classes", total_classes)
    c3.metric("Total Constraints", total_constraints)
    c4.metric("Conflicts", conflicts)

    st.divider()
    if st.button("Generate Timetable", type="primary"):
        st.session_state["generated_result"] = generate_schedule(data)
        st.success("Timetable generated from uploaded JSON.")


def render_timetable():
    st.header("Weekly Timetable")

    if not data:
        st.warning("Upload JSON first.")
        return

    gen = st.session_state.get("generated_result")
    if not gen:
        st.info("Go to Dashboard and click 'Generate Timetable'.")
        return

    classes = data.get("classes", [])
    cls = st.selectbox("Select Class", classes, index=0)
    df = build_class_dataframe(gen, cls)

    st.dataframe(df.style.applymap(conflict_style), use_container_width=True, height=500)
    st.info("Cells marked with ⚠ are unresolved/conflict slots.")


def render_constraints():
    st.header("Constraints")
    if not data:
        st.warning("Upload JSON first.")
        return

    weights = data.get("weights", {})
    st.subheader("Soft Weights")
    edited = {}
    for k, v in weights.items():
        edited[k] = st.slider(k, 0, 20, int(v))

    st.subheader("Basic Limits")
    max_consecutive = st.number_input(
        "max_consecutive_periods",
        min_value=1,
        max_value=10,
        value=int(data.get("max_consecutive_periods", 4)),
    )

    if st.button("Save Constraints", type="primary"):
        st.session_state["saved_constraints"] = {
            "weights": edited,
            "max_consecutive_periods": max_consecutive,
        }
        st.success("Constraints saved (mock).")


def render_export():
    st.header("Export")

    gen = st.session_state.get("generated_result")
    if not gen:
        st.info("Generate timetable first.")
        return

    classes = list(gen["schedule"].keys())
    selected = st.selectbox("Export scope", ["All Classes"] + classes)
    class_filter = None if selected == "All Classes" else selected

    export_df = build_export_dataframe(gen, class_filter)

    st.caption(f"Rows to export: {len(export_df)}")
    st.dataframe(export_df.head(20), use_container_width=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scope = "all_classes" if class_filter is None else class_filter.replace(" ", "_")

    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    excel_bytes = dataframe_to_excel_bytes(export_df)
    pdf_bytes = dataframe_to_pdf_bytes(export_df, title=f"Timetable Export - {selected}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name=f"timetable_{scope}_{ts}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        if excel_bytes is not None:
            st.download_button(
                "Download Excel",
                data=excel_bytes,
                file_name=f"timetable_{scope}_{ts}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.warning("Excel export unavailable. Install openpyxl.")
    with c3:
        if pdf_bytes is not None:
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"timetable_{scope}_{ts}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.warning("PDF export unavailable. Install reportlab.")


if page == "Dashboard":
    render_dashboard()
elif page == "Timetable":
    render_timetable()
elif page == "Constraints":
    render_constraints()
else:
    render_export()