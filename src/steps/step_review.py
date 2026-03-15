"""Step 2 – Review Posts: Run CrewAI agents, edit, approve posts."""

import streamlit as st
from src.state_manager import StateManager
from src.services.generator_service import generate_posts, regenerate_single_post
from src.models import PostStatus, PLATFORM_LIMITS, PLATFORM_ICONS, PLATFORM_COLORS
from src.exceptions import GenerationError, APIKeyError
from src.logger import get_logger

logger = get_logger(__name__)


def render_review(state: StateManager):
    st.markdown('<div class="section-title">✍️ Review & Edit Posts</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">'
        "Your 4-agent CrewAI pipeline generates, drafts, edits, and hashtags every post."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Agent pipeline visual ─────────────────────────────────────────────
    with st.expander("🤖 How the Multi-Agent Pipeline Works", expanded=not state.posts_generated):
        st.markdown("""
<div style="display:flex; gap:12px; flex-wrap:wrap; margin:0.5rem 0 1rem">
  <div style="flex:1; min-width:140px; background:#f0f9ff; border:1px solid #bae6fd;
              border-radius:10px; padding:12px; text-align:center">
    <div style="font-size:1.6rem">🧠</div>
    <div style="font-weight:700; color:#0369a1; font-size:0.85rem">1. Strategist</div>
    <div style="font-size:0.75rem; color:#64748b; margin-top:4px">
      Analyzes topic, picks the best content angle & key messages
    </div>
  </div>
  <div style="display:flex; align-items:center; color:#94a3b8; font-size:1.2rem">→</div>
  <div style="flex:1; min-width:140px; background:#fdf4ff; border:1px solid #e9d5ff;
              border-radius:10px; padding:12px; text-align:center">
    <div style="font-size:1.6rem">✍️</div>
    <div style="font-weight:700; color:#7e22ce; font-size:0.85rem">2. Copywriter</div>
    <div style="font-size:0.75rem; color:#64748b; margin-top:4px">
      Writes a compelling draft with a strong hook
    </div>
  </div>
  <div style="display:flex; align-items:center; color:#94a3b8; font-size:1.2rem">→</div>
  <div style="flex:1; min-width:140px; background:#fff7ed; border:1px solid #fed7aa;
              border-radius:10px; padding:12px; text-align:center">
    <div style="font-size:1.6rem">🔍</div>
    <div style="font-weight:700; color:#c2410c; font-size:0.85rem">3. Editor</div>
    <div style="font-size:0.75rem; color:#64748b; margin-top:4px">
      Polishes tone, enforces character limits, cuts filler
    </div>
  </div>
  <div style="display:flex; align-items:center; color:#94a3b8; font-size:1.2rem">→</div>
  <div style="flex:1; min-width:140px; background:#f0fdf4; border:1px solid #86efac;
              border-radius:10px; padding:12px; text-align:center">
    <div style="font-size:1.6rem">#️⃣</div>
    <div style="font-weight:700; color:#15803d; font-size:0.85rem">4. Hashtag Expert</div>
    <div style="font-size:0.75rem; color:#64748b; margin-top:4px">
      Selects optimal hashtags & assembles the final post
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        cfg  = state.config
        data = state.sample_data
        n_platforms = len(cfg.get("platforms", []))
        n_topics    = len(data.get("topics", []))
        n_variants  = cfg.get("num_posts", 2)
        total_crews = n_platforms * n_topics * n_variants
        st.info(
            f"⚙️ Your configuration will run **{total_crews} crews** "
            f"({n_platforms} platforms × {n_topics} topics × {n_variants} variants). "
            "Each crew makes **4 sequential LLM calls**."
        )

    # ── Generate button ───────────────────────────────────────────────────
    col_gen, col_stats = st.columns([1, 3])
    with col_gen:
        label = "🔄 Regenerate All" if state.posts_generated else "🚀 Run Agent Crews"
        if st.button(label, type="primary", use_container_width=True):
            _run_generation(state)

    with col_stats:
        if state.posts_generated:
            posts    = state.generated_posts
            approved = sum(1 for p in posts if p["status"] == PostStatus.APPROVED)
            total    = len(posts)
            st.markdown(
                f'<div class="info-card">📊 <strong>{total}</strong> posts generated · '
                f'<strong>{approved}</strong> approved · '
                f'<strong>{total - approved}</strong> pending</div>',
                unsafe_allow_html=True,
            )

    if not state.posts_generated:
        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("← Back", use_container_width=True):
                state.prev_step()
        return

    # ── Filters ───────────────────────────────────────────────────────────
    posts     = state.generated_posts
    platforms = list(dict.fromkeys(p["platform"] for p in posts))
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_platform = st.selectbox("Filter by Platform", ["All"] + platforms)
    with col_f2:
        filter_status   = st.selectbox("Filter by Status",
                                       ["All", PostStatus.DRAFT, PostStatus.APPROVED])
    with col_f3:
        sort_by = st.selectbox("Sort by", ["Platform", "Topic", "Status"])

    # ── Bulk actions ──────────────────────────────────────────────────────
    col_ba1, col_ba2, _ = st.columns([1, 1, 4])
    with col_ba1:
        if st.button("✅ Approve All", use_container_width=True):
            for p in st.session_state["generated_posts"]:
                p["status"] = PostStatus.APPROVED
            st.rerun()
    with col_ba2:
        if st.button("↩️ Reset All", use_container_width=True):
            for p in st.session_state["generated_posts"]:
                p["status"] = PostStatus.DRAFT
            st.rerun()

    st.markdown("---")

    # ── Filter + sort ─────────────────────────────────────────────────────
    filtered = posts
    if filter_platform != "All":
        filtered = [p for p in filtered if p["platform"] == filter_platform]
    if filter_status != "All":
        filtered = [p for p in filtered if p["status"] == filter_status]
    filtered = sorted(filtered, key={"Platform": lambda p: p["platform"],
                                      "Topic":    lambda p: p.get("topic", ""),
                                      "Status":   lambda p: p["status"]}[sort_by])

    if not filtered:
        st.info("No posts match the current filter.")
    else:
        _render_posts_grid(state, filtered)

    # ── Navigation ────────────────────────────────────────────────────────
    st.markdown("---")
    approved_posts = [p for p in posts if p["status"] == PostStatus.APPROVED]
    col_back, col_next, col_info = st.columns([1, 1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            state.prev_step()
    with col_next:
        if st.button("Publish →", type="primary", use_container_width=True,
                     disabled=len(approved_posts) == 0):
            state.next_step()
    with col_info:
        if not approved_posts:
            st.warning("⚠️ Approve at least one post to proceed to publishing.")
        else:
            st.success(f"✅ {len(approved_posts)} post(s) approved and ready to publish.")


def _render_posts_grid(state: StateManager, posts: list):
    platforms = list(dict.fromkeys(p["platform"] for p in posts))
    for platform in platforms:
        plat_posts = [p for p in posts if p["platform"] == platform]
        icon  = PLATFORM_ICONS.get(platform, "📱")
        color = PLATFORM_COLORS.get(platform, "#6366f1")
        st.markdown(
            f"<h4 style='color:{color}; margin-top:1.5rem'>{icon} {platform}</h4>",
            unsafe_allow_html=True,
        )
        for post in plat_posts:
            _render_post_card(state, post, platform)


def _render_post_card(state: StateManager, post: dict, platform: str):
    post_id  = post["id"]
    status   = post["status"]
    char_limit = PLATFORM_LIMITS.get(platform, 2000)
    current    = post.get("edited_content") or post.get("content", "")

    status_color = "#10b981" if status == PostStatus.APPROVED else "#f59e0b"
    status_icon  = "✅" if status == PostStatus.APPROVED else "📝"

    st.markdown(
        f"<div class='post-card'>"
        f"<div style='display:flex; justify-content:space-between; margin-bottom:0.75rem'>"
        f"<span style='font-size:0.8rem; font-weight:600; color:#64748b'>"
        f"🏷️ {post.get('topic','—')}</span>"
        f"<span style='font-size:0.78rem; font-weight:600; color:{status_color}'>"
        f"{status_icon} {status.upper()}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    edited = st.text_area("Post content", value=current, height=130,
                           key=f"edit_{post_id}", label_visibility="collapsed")

    char_count  = len(edited)
    over_limit  = char_count > char_limit
    cnt_color   = "#ef4444" if over_limit else "#64748b"
    st.markdown(
        f"<div style='font-size:0.75rem; color:{cnt_color}; text-align:right; "
        f"margin-top:-0.5rem'>"
        f"{char_count}/{char_limit} chars {'⚠️ Over limit!' if over_limit else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if post.get("hashtags"):
        tags_html = " ".join(
            [f"<code style='font-size:0.75rem'>#{h}</code>" for h in post["hashtags"]]
        )
        st.markdown(tags_html, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        approve_label = "✅ Approved" if status == PostStatus.APPROVED else "👍 Approve"
        if st.button(approve_label, key=f"approve_{post_id}", use_container_width=True):
            new_status = PostStatus.DRAFT if status == PostStatus.APPROVED else PostStatus.APPROVED
            for p in st.session_state["generated_posts"]:
                if p["id"] == post_id:
                    p["edited_content"] = edited
                    p["status"] = new_status
                    break
            st.rerun()
    with col2:
        if st.button("🔄 Regenerate", key=f"regen_{post_id}", use_container_width=True):
            with st.spinner("Running agent crew…"):
                try:
                    new_post = regenerate_single_post(state.config, state.sample_data, post)
                    for i, p in enumerate(st.session_state["generated_posts"]):
                        if p["id"] == post_id:
                            st.session_state["generated_posts"][i] = new_post
                            break
                    st.rerun()
                except Exception as e:
                    st.error(f"Regeneration failed: {e}")
    with col3:
        if edited != current:
            if st.button("💾 Save edit", key=f"save_{post_id}", use_container_width=True):
                for p in st.session_state["generated_posts"]:
                    if p["id"] == post_id:
                        p["edited_content"] = edited
                        p["char_count"]     = len(edited)
                        break
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("")


def _run_generation(state: StateManager):
    cfg  = state.config
    data = state.sample_data

    platforms  = cfg.get("platforms", [])
    topics     = data.get("topics", [])
    num_posts  = cfg.get("num_posts", 2)
    total_crews = len(platforms) * len(topics) * num_posts

    progress    = st.progress(0)
    status_text = st.empty()
    completed   = [0]

    status_text.info(
        f"🤖 Running {total_crews} agent crews "
        f"(4 agents × {total_crews} runs = {total_crews * 4} LLM calls)…"
    )

    try:
        posts = generate_posts(cfg, data)
        progress.progress(100)
        status_text.success(f"✅ {len(posts)} posts generated by your agent crew!")
        state.set_generated_posts(posts)
        st.rerun()
    except APIKeyError as e:
        progress.empty()
        status_text.error(f"🔑 API Key error: {e}")
    except GenerationError as e:
        progress.empty()
        status_text.error(f"❌ Agent crew failed: {e}")
    except Exception as e:
        progress.empty()
        status_text.error(f"💥 Unexpected error: {e}")
        logger.exception("Unexpected generation error")
