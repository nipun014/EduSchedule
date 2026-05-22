import io
import json
from collections import defaultdict
from datetime import datetime

import pandas as pd
import streamlit as st

# =========================================================
# Page config (MUST be first Streamlit call)
# =========================================================
st.set_page_config(page_title="Timetable Manager", layout="wide")

# =========================================================
# Global CSS (dark admin theme)
# =========================================================
st.markdown(
    """
    <style>
    .stApp {
        background-color: #191919;
        color: #e5e7eb;
    }

    section[data-testid="stSidebar"] {
        background-color: #0A1222;
        border-right: 1px solid #334155;
    }

    header[data-testid="stHeader"] {
        background-color: #191919;
        border-bottom: 1px solid #334155;
    }

    .stButton > button,
    .stDownloadButton > button {
        background-color: #0e43ad;
        color: #ffffff;
        border: 1px solid #334155;
        box-shadow: none;
    }

    [data-baseweb="input"] > div,
    [data-baseweb="select"] > div {
        background-color: #0f172a;
        border: 1px solid #334155;
        color: #e5e7eb;
    }

    [data-testid="stDataFrame"],
    [data-testid="stMetric"] {
        background-color: #0f172a;
        border: 1px solid #334155;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# JSON parsing / validation
# =========================================================
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
    return base[:days_count] if days_count <= len(base) else [f"Day {i+1}" for i in range(days_count)]


def get_period_labels(periods_per_day: int) -> list[str]:
    return [f"Period {i+1}" for i in range(periods_per_day)]

# =========================================================
# Timetable generator (greedy)
# =========================================================
def generate_schedule(data: dict) -> dict:
    classes = data["classes"]
    subjects = data["subjects"]
    teachers = data["teachers"]
    class_subjects = data["class_subjects"]
    rooms = data.get("rooms", {})

    days = int(data["days"])
    periods = int(data["periods_per_day"])

    teachers_by_subject = defaultdict(list)
    for tid, tinfo in teachers.items():
        for s in tinfo.get("can_teach", []):
            teachers_by_subject[s].append(tid)

    rooms_by_type = defaultdict(list)
    for rid, rinfo in rooms.items():
        rooms_by_type[rinfo.get("type", "standard")].append(rid)

    remaining = {
        cls: {
            sub: int(subjects.get(sub, {}).get("hours_per_week", 0))
            for sub in class_subjects.get(cls, [])
        }
        for cls in classes
    }

    teacher_busy = defaultdict(set)
    room_busy = defaultdict(set)

    schedule = {cls: {} for cls in classes}
    conflicts = 0

    for d in range(days):
        for p in range(periods):
            for cls in classes:
                candidates = [s for s, hrs in remaining[cls].items() if hrs > 0]

                if not candidates:
                    schedule[cls][(d, p)] = {
                        "subject": "Free",
                        "teacher": "-",
                        "room": "-",
                        "conflict": False,
                    }
                    continue

                candidates.sort(key=lambda s: remaining[cls][s], reverse=True)
                assigned = False

                for sub in candidates:
                    for tid in teachers_by_subject.get(sub, []):
                        availability = teachers[tid].get("availability", [])
                        if (
                            d < len(availability)
                            and p < len(availability[d])
                            and availability[d][p] == 1
                            and tid not in teacher_busy[(d, p)]
                        ):
                            schedule[cls][(d, p)] = {
                                "subject": sub,
                                "teacher": tid,
                                "room": "-",
                                "conflict": False,
                            }
                            remaining[cls][sub] -= 1
                            teacher_busy[(d, p)].add(tid)
                            assigned = True
                            break
                    if assigned:
                        break

                if not assigned:
                    schedule[cls][(d, p)] = {
                        "subject": "Unassigned",
                        "teacher": "N/A",
                        "room": "N/A",
                        "conflict": True,
                    }
                    conflicts += 1

    return {"schedule": schedule, "conflicts": conflicts, "days": days, "periods": periods}

# =========================================================
# Sidebar
# =========================================================
st.sidebar.title("EduSchedule")
page = st.sidebar.radio("Go to", ["Dashboard", "Timetable", "Constraints", "Export"])

st.sidebar.subheader("EduSchedule Input")
uploaded_json = st.sidebar.file_uploader("Upload timetable JSON", type=["json"])
parsed = parse_uploaded_json(uploaded_json)
if parsed:
    st.session_state["input_data"] = parsed

data = st.session_state.get("input_data")

# =========================================================
# Pages
# =========================================================
def render_dashboard():
    has_data = data is not None
    st.title("EduSchedule")
    st.caption("Smart Academic Timetable Management System")

    total_teachers = len(data.get("teachers", {})) if has_data else 0
    total_classes = len(data.get("classes", [])) if has_data else 0
    total_constraints = len(data.get("weights", {})) + 3 if has_data else 0

    generated = st.session_state.get("generated_result")
    conflicts = generated.get("conflicts", 0) if generated else 0

    c1, c2, c3, c4 = st.columns(4, gap="small")
    c1.metric("Total Teachers", total_teachers)
    c2.metric("Total Classes", total_classes)
    c3.metric("Total Constraints", total_constraints)
    c4.metric("Conflicts", conflicts)

    if not has_data:
        st.warning("Please upload your JSON file from the sidebar.")
        st.info("Dashboard metrics and timetable generation will be enabled after upload.")
        return

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        if st.button("Generate Timetable", type="primary", use_container_width=True):
            st.session_state["generated_result"] = generate_schedule(data)
            st.success("Timetable generated successfully.")

def render_timetable():
    st.header("Weekly Timetable")

    gen = st.session_state.get("generated_result")
    if not gen:
        st.info("Generate a timetable from the Dashboard first.")
        return

    classes = data.get("classes", [])
    cls = st.selectbox("Select Class", classes)
    day_labels = get_day_labels(gen["days"])
    period_labels = get_period_labels(gen["periods"])

    df = pd.DataFrame("", index=period_labels, columns=day_labels)
    for d in range(gen["days"]):
        for p in range(gen["periods"]):
            item = gen["schedule"][cls][(d, p)]
            df.iloc[p, d] = f'{item["subject"]}\n{item["teacher"]}'

    st.dataframe(df, use_container_width=True, height=500)

def render_constraints():
    st.header("Constraints")

    if not data:
        st.warning("Upload JSON first.")
        return

    st.caption("Adjust soft preferences for experimentation (prototype mode).")

    weights = data.get("weights", {})
    edited = {}

    with st.container(border=True):
        st.subheader("Soft Weights")
        if not weights:
            st.info("No weight settings found in uploaded JSON.")
        for key, value in weights.items():
            edited[key] = st.slider(key, 0, 20, int(value))

    with st.container(border=True):
        st.subheader("Basic Limits")
        max_consecutive = st.number_input(
            "max_consecutive_periods",
            min_value=1,
            max_value=10,
            value=int(data.get("max_consecutive_periods", 4)),
        )

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        if st.button("Save Constraints", type="primary", use_container_width=True):
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

    rows = []
    for cls, slots in gen["schedule"].items():
        for (d, p), item in slots.items():
            rows.append({
                "Class": cls,
                "Day": get_day_labels(gen["days"])[d],
                "Period": get_period_labels(gen["periods"])[p],
                "Subject": item["subject"],
                "Teacher": item["teacher"],
            })

    df = pd.DataFrame(rows)
    st.dataframe(df.head(20), use_container_width=True)

    csv_bytes = df.to_csv(index=False).encode("utf-8")

    excel_bytes = None
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Timetable")
        buffer.seek(0)
        excel_bytes = buffer.read()
    except Exception:
        excel_bytes = None

    c1, c2 = st.columns(2, gap="small")
    with c1:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="timetable.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        if excel_bytes is not None:
            st.download_button(
                "Download Excel",
                data=excel_bytes,
                file_name="timetable.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.warning("Excel export unavailable. Install openpyxl.")

# =========================================================
# Routing
# =========================================================
if page == "Dashboard":
    render_dashboard()
elif page == "Timetable":
    render_timetable()
elif page == "Constraints":
    render_constraints()
else:
    render_export()