"""
Social Media Generator — Main Streamlit App
Step-based wizard: Configure → Upload Data → Review Posts → Publish
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from src.state_manager import StateManager
from src.steps.step_configure import render_configure
from src.steps.step_upload import render_upload
from src.steps.step_review import render_review
from src.steps.step_publish import render_publish
from src.logger import get_logger

logger = get_logger(__name__)

st.set_page_config(
    page_title="Social Media Generator",
    page_icon="📣",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
    padding: 2rem 2.5rem 1.5rem;
    border-radius: 16px;
    margin-bottom: 2rem;
    color: white;
}
.main-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.main-header p  { margin: 0.25rem 0 0; opacity: 0.85; font-size: 1rem; }

/* Stepper */
.stepper-container {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 2.5rem;
    padding: 1.25rem 2rem;
    background: #f8fafc;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}
.step-item {
    display: flex; flex-direction: column;
    align-items: center; flex: 1; position: relative;
}
.step-circle {
    width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.9rem;
    transition: all 0.3s ease; z-index: 1;
}
.step-circle.active  { background: #6366f1; color: white; box-shadow: 0 0 0 4px rgba(99,102,241,0.2); }
.step-circle.done    { background: #10b981; color: white; }
.step-circle.pending { background: #e2e8f0; color: #94a3b8; }
.step-label { font-size: 0.75rem; font-weight: 500; margin-top: 0.4rem; text-align: center; width: 90px; }
.step-label.active  { color: #6366f1; }
.step-label.done    { color: #10b981; }
.step-label.pending { color: #94a3b8; }
.step-connector { height: 2px; flex: 1; max-width: 80px; margin-bottom: 1.2rem; border-radius: 2px; }
.step-connector.done    { background: #10b981; }
.step-connector.pending { background: #e2e8f0; }

/* Cards */
.info-card    { background:#f0f9ff; border:1px solid #bae6fd; border-radius:10px; padding:1rem 1.25rem; margin-bottom:1rem; color:#0c4a6e; font-size:0.9rem; }
.success-card { background:#f0fdf4; border:1px solid #86efac; border-radius:10px; padding:1rem 1.25rem; margin-bottom:1rem; color:#14532d; font-size:0.9rem; }

.post-card { background:white; border:1px solid #e2e8f0; border-radius:12px; padding:1.25rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.06); }
.post-card:hover { box-shadow:0 4px 12px rgba(0,0,0,0.1); }

.stButton > button { border-radius:8px !important; font-weight:600 !important; transition:all 0.2s !important; }
.stButton > button:hover { transform:translateY(-1px); }

.section-title    { font-size:1.3rem; font-weight:700; color:#1e293b; margin-bottom:0.25rem; }
.section-subtitle { font-size:0.9rem; color:#64748b; margin-bottom:1.5rem; }
</style>
""", unsafe_allow_html=True)

STEPS = [
    {"id": 0, "label": "⚙️ Configure"},
    {"id": 1, "label": "📂 Upload Data"},
    {"id": 2, "label": "✍️ Review Posts"},
    {"id": 3, "label": "🚀 Publish"},
]


def render_stepper(state: StateManager):
    """Render the visual stepper. Completed steps are clickable to go back."""
    current = state.current_step
    parts = []
    for i, step in enumerate(STEPS):
        if i < current:
            status, icon = "done", "✓"
        elif i == current:
            status, icon = "active", str(i + 1)
        else:
            status, icon = "pending", str(i + 1)

        parts.append(
            f'<div class="step-item">'
            f'  <div class="step-circle {status}">{icon}</div>'
            f'  <div class="step-label {status}">{step["label"]}</div>'
            f"</div>"
        )
        if i < len(STEPS) - 1:
            conn = "done" if i < current else "pending"
            parts.append(f'<div class="step-connector {conn}"></div>')

    st.markdown(
        '<div class="stepper-container">' + "".join(parts) + "</div>",
        unsafe_allow_html=True,
    )

    # Clickable "jump back" buttons rendered below stepper as compact tabs
    if current > 0:
        cols = st.columns(len(STEPS))
        for i, step in enumerate(STEPS):
            with cols[i]:
                if i < current:
                    if st.button(
                        f"← {step['label']}",
                        key=f"nav_back_{i}",
                        use_container_width=True,
                        help=f"Go back to {step['label']}",
                    ):
                        state.go_to(i)
        st.markdown("")   # spacing


def main():
    state = StateManager()

    st.markdown("""
        <div class="main-header">
            <h1>📣 Social Media Generator</h1>
            <p>Multi-agent AI content generation — from brand data to published posts in 4 steps</p>
        </div>
    """, unsafe_allow_html=True)

    render_stepper(state)

    step = state.current_step
    if step == 0:
        render_configure(state)
    elif step == 1:
        render_upload(state)
    elif step == 2:
        render_review(state)
    elif step == 3:
        render_publish(state)

    st.markdown("---")
    st.markdown(
        "<p style='text-align:center; color:#94a3b8; font-size:0.8rem;'>"
        "Social Media Generator · Powered by CrewAI + LangChain + Streamlit"
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
