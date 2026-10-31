from pathlib import Path
import streamlit as st

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

attendance_page = HERE / "app.py"
attrition_page = ROOT / "Phase 2" / "Task 7" / "app.py"

st.set_page_config(
    page_title="PulseIQ | Workforce Analytics",
    page_icon="📊",
    layout="wide",
)

pages = [
    st.Page(
        str(attendance_page),
        title="Attendance & Leave",
        icon="📊",
        url_path="attendance-leave",
        default=True,
    ),
    st.Page(
        str(attrition_page),
        title="Attrition Analytics",
        icon="📉",
        url_path="attrition-analytics",
    ),
]

navigation = st.navigation(pages, position="sidebar")
navigation.run()
