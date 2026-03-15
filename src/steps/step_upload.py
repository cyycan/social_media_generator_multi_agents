"""Step 1 – Upload Data: CSV upload, text paste, or manual entry."""

import streamlit as st
from src.state_manager import StateManager
from src.services.data_service import parse_csv, parse_text, parse_manual, get_sample_csv
from src.exceptions import DataParsingError
from src.logger import get_logger

logger = get_logger(__name__)


def render_upload(state: StateManager):
    st.markdown('<div class="section-title">📂 Upload Sample Data</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        "Provide topics, keywords, and context that the AI will use to generate your posts."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Download sample CSV ───────────────────────────────────────────────
    with st.expander("📥 Download a sample CSV template", expanded=False):
        st.markdown(
            "Your CSV can have columns: **topic**, **keywords**, **context**. "
            "Only `topic` is required."
        )
        st.download_button(
            "⬇️ Download sample_data.csv",
            data=get_sample_csv(),
            file_name="sample_data.csv",
            mime="text/csv",
        )

    # ── Input method tabs ─────────────────────────────────────────────────
    tab_csv, tab_text, tab_manual = st.tabs(["📄 Upload CSV", "✏️ Paste Text", "⌨️ Manual Entry"])

    data_result = None
    input_method = None

    # ── Tab 1: CSV Upload ─────────────────────────────────────────────────
    with tab_csv:
        st.markdown("Upload a CSV file with your topics, keywords, and optional context.")
        uploaded = st.file_uploader(
            "Choose CSV file",
            type=["csv"],
            help="Max 200MB. Columns: topic, keywords, context",
        )
        if uploaded:
            try:
                data_result = parse_csv(uploaded.read())
                input_method = "csv"
                st.markdown(
                    f'<div class="success-card">✅ Parsed <strong>{len(data_result["topics"])}</strong> topics '
                    f'and <strong>{len(data_result["keywords"])}</strong> keywords from <em>{uploaded.name}</em></div>',
                    unsafe_allow_html=True,
                )
                _show_data_preview(data_result)
            except DataParsingError as e:
                st.error(f"❌ Could not parse file: {e}")

    # ── Tab 2: Paste Text ─────────────────────────────────────────────────
    with tab_text:
        st.markdown(
            "Paste any text — bullet points, notes, article excerpts. "
            "Each line becomes a topic. Include **#hashtags** to auto-extract keywords."
        )
        text_input = st.text_area(
            "Paste your content here",
            height=200,
            placeholder="- New AI features in our product\n- Customer success story #testimonial #results\n- Industry report: AI trends 2025 #AI #trends",
            value=state.sample_data.get("raw_text", "") if state.sample_data.get("raw_text", "").startswith("-") or "\n" in state.sample_data.get("raw_text", "") else "",
        )
        if text_input.strip():
            try:
                data_result = parse_text(text_input)
                input_method = "text"
                st.markdown(
                    f'<div class="success-card">✅ Extracted <strong>{len(data_result["topics"])}</strong> topics '
                    f'and <strong>{len(data_result["keywords"])}</strong> keywords</div>',
                    unsafe_allow_html=True,
                )
                _show_data_preview(data_result)
            except DataParsingError as e:
                st.error(f"❌ {e}")

    # ── Tab 3: Manual Entry ───────────────────────────────────────────────
    with tab_manual:
        st.markdown("Enter your topics, keywords, and context directly.")

        existing = state.sample_data
        col_l, col_r = st.columns(2, gap="medium")

        with col_l:
            topics_input = st.text_area(
                "Topics (one per line) *",
                height=160,
                placeholder="Product launch announcement\nCustomer success story\nIndustry insights\nTeam culture spotlight",
                value="\n".join(existing.get("topics", [])),
            )
            keywords_input = st.text_input(
                "Keywords (comma-separated)",
                placeholder="innovation, AI, SaaS, growth, technology",
                value=", ".join(existing.get("keywords", [])),
            )

        with col_r:
            extra_context = st.text_area(
                "Extra Context / Brand Notes",
                height=160,
                placeholder="Add anything useful: target audience, product details, upcoming events, campaigns...",
                value=existing.get("extra_context", ""),
            )

        if topics_input.strip():
            try:
                data_result = parse_manual(topics_input, keywords_input, extra_context)
                input_method = "manual"
                st.markdown(
                    f'<div class="success-card">✅ Ready: <strong>{len(data_result["topics"])}</strong> topics, '
                    f'<strong>{len(data_result["keywords"])}</strong> keywords</div>',
                    unsafe_allow_html=True,
                )
            except DataParsingError as e:
                st.error(f"❌ {e}")

    # ── Navigation ────────────────────────────────────────────────────────
    st.markdown("---")
    col_back, col_next, col_info = st.columns([1, 1, 3])

    with col_back:
        if st.button("← Back", use_container_width=True):
            state.prev_step()

    with col_next:
        can_proceed = data_result is not None
        if st.button(
            "Save & Continue →",
            type="primary",
            use_container_width=True,
            disabled=not can_proceed,
        ):
            if not data_result:
                st.warning("Please provide data before continuing.")
                st.stop()
            state.update_sample_data(**data_result)
            # Reset generated posts when data changes
            state.set("posts_generated", False)
            state.set("generated_posts", [])
            state.next_step()

    with col_info:
        if not data_result:
            st.info("ℹ️ Upload a CSV, paste text, or fill in the manual entry tab above to continue.")
        else:
            cfg = state.config
            platforms = cfg.get("platforms", [])
            topics = data_result.get("topics", [])
            num_posts = cfg.get("num_posts", 3)
            total = len(platforms) * len(topics) * num_posts
            st.success(
                f"✅ Ready to generate ~**{total}** posts "
                f"({len(platforms)} platforms × {len(topics)} topics × {num_posts} variants)"
            )


def _show_data_preview(data: dict):
    with st.expander("👁️ Preview extracted data", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Topics**")
            for t in data.get("topics", [])[:10]:
                st.markdown(f"• {t}")
            if len(data.get("topics", [])) > 10:
                st.caption(f"… and {len(data['topics']) - 10} more")
        with col2:
            st.markdown("**Keywords**")
            kws = data.get("keywords", [])
            if kws:
                st.markdown(" ".join([f"`{k}`" for k in kws[:20]]))
            else:
                st.caption("None extracted")
        if data.get("extra_context"):
            st.markdown(f"**Context:** {data['extra_context'][:300]}")
