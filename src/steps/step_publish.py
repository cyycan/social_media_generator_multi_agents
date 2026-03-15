"""Step 3 – Publish: Send approved posts to social media platforms."""

import streamlit as st
from src.state_manager import StateManager
from src.services.publisher_service import publish_post
from src.models import PostStatus, PLATFORM_ICONS, PLATFORM_COLORS
from src.logger import get_logger

logger = get_logger(__name__)


def render_publish(state: StateManager):
    st.markdown('<div class="section-title">🚀 Publish Posts</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Review your approved posts and publish them to your platforms.</div>',
        unsafe_allow_html=True,
    )

    approved_posts = [
        p for p in state.generated_posts if p["status"] == PostStatus.APPROVED
    ]

    if not approved_posts:
        st.warning("⚠️ No approved posts found. Go back to Review and approve posts first.")
        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("← Back to Review", use_container_width=True):
                state.prev_step()
        return

    # ── Publish mode selector ─────────────────────────────────────────────
    st.markdown("#### 🔧 Publishing Mode")
    col_mode, col_info = st.columns([1, 2])

    with col_mode:
        publish_mode = st.radio(
            "Mode",
            options=["🧪 Mock (Safe Test)", "🔗 Live API"],
            help="Mock mode simulates publishing without real API calls.",
        )
    use_mock = "Mock" in publish_mode

    with col_info:
        if use_mock:
            st.markdown(
                '<div class="info-card">🧪 <strong>Mock Mode</strong>: No real posts will be created. '
                "Perfect for testing your workflow end-to-end. Posts will be marked as 'published' "
                "with fake IDs.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="info-card">🔗 <strong>Live Mode</strong>: Posts will be sent to the real '
                "platform APIs. Ensure your platform credentials below are configured correctly. "
                "Currently <strong>Twitter/X</strong> and <strong>LinkedIn</strong> are fully supported.</div>",
                unsafe_allow_html=True,
            )

    # ── Live credentials (only shown in Live mode) ────────────────────────
    platform_credentials: dict = {}
    if not use_mock:
        with st.expander("🔑 Platform Credentials", expanded=True):
            platforms_needed = list(dict.fromkeys(p["platform"] for p in approved_posts))

            if "Twitter/X" in platforms_needed:
                st.markdown("**Twitter/X**")
                col_a, col_b = st.columns(2)
                with col_a:
                    tw_key = st.text_input("API Key", type="password", key="tw_key")
                    tw_secret = st.text_input("API Secret", type="password", key="tw_secret")
                with col_b:
                    tw_token = st.text_input("Access Token", type="password", key="tw_token")
                    tw_token_secret = st.text_input("Access Token Secret", type="password", key="tw_token_sec")
                platform_credentials["Twitter/X"] = {
                    "api_key": tw_key,
                    "api_secret": tw_secret,
                    "access_token": tw_token,
                    "access_token_secret": tw_token_secret,
                }

            if "LinkedIn" in platforms_needed:
                st.markdown("**LinkedIn**")
                col_a, col_b = st.columns(2)
                with col_a:
                    li_token = st.text_input("Access Token", type="password", key="li_token")
                with col_b:
                    li_urn = st.text_input(
                        "Author URN",
                        placeholder="urn:li:person:xxxxxxxx",
                        key="li_urn",
                    )
                platform_credentials["LinkedIn"] = {
                    "access_token": li_token,
                    "author_urn": li_urn,
                }

    # ── Posts preview ─────────────────────────────────────────────────────
    st.markdown(f"#### 📋 {len(approved_posts)} Posts Ready to Publish")

    platforms = list(dict.fromkeys(p["platform"] for p in approved_posts))
    for platform in platforms:
        plat_posts = [p for p in approved_posts if p["platform"] == platform]
        icon = PLATFORM_ICONS.get(platform, "📱")
        color = PLATFORM_COLORS.get(platform, "#6366f1")

        st.markdown(
            f"<h5 style='color:{color}; margin:1rem 0 0.5rem'>{icon} {platform} ({len(plat_posts)} posts)</h5>",
            unsafe_allow_html=True,
        )

        for post in plat_posts:
            content = post.get("edited_content") or post.get("content", "")
            st.markdown(
                f"<div class='post-card' style='border-left: 3px solid {color}'>"
                f"<p style='font-size:0.85rem; color:#334155; margin:0'>{content[:300]}"
                f"{'…' if len(content) > 300 else ''}</p>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Publish button ────────────────────────────────────────────────────
    st.markdown("---")
    col_back, col_pub, col_spacer = st.columns([1, 2, 2])

    with col_back:
        if st.button("← Back", use_container_width=True):
            state.prev_step()

    with col_pub:
        pub_label = (
            f"🚀 Publish {len(approved_posts)} Post{'s' if len(approved_posts) > 1 else ''}"
            + (" (Mock)" if use_mock else " (Live)")
        )
        if st.button(pub_label, type="primary", use_container_width=True):
            _run_publish(state, approved_posts, use_mock, platform_credentials)

    # ── Results ───────────────────────────────────────────────────────────
    if state.publish_results:
        _render_results(state)


def _run_publish(
    state: StateManager,
    posts: list,
    use_mock: bool,
    credentials: dict,
):
    """Execute publishing with a progress bar."""
    state.set("publish_results", [])

    progress = st.progress(0)
    status = st.empty()

    for i, post in enumerate(posts):
        platform = post["platform"]
        status.info(f"📤 Publishing to {platform} ({i+1}/{len(posts)})…")
        progress.progress((i + 1) / len(posts))

        try:
            result = publish_post(
                post,
                use_mock=use_mock,
                platform_credentials=credentials,
            )
            state.add_publish_result(result)

            # Update post status in session
            for p in st.session_state["generated_posts"]:
                if p["id"] == post["id"]:
                    p["status"] = result["status"]
                    break

        except Exception as e:
            logger.error(f"Publish error for {platform}: {e}")
            state.add_publish_result({
                "post_id": post["id"],
                "platform": platform,
                "status": PostStatus.FAILED,
                "platform_post_id": None,
                "published_at": None,
                "url": None,
                "error": str(e),
            })

    progress.progress(100)
    results = state.publish_results
    success_count = sum(1 for r in results if r["status"] == PostStatus.PUBLISHED)
    fail_count = len(results) - success_count

    if fail_count == 0:
        status.success(f"🎉 All {success_count} posts published successfully!")
    else:
        status.warning(
            f"📊 Published: {success_count} ✅ | Failed: {fail_count} ❌"
        )

    st.rerun()


def _render_results(state: StateManager):
    results = state.publish_results
    success = [r for r in results if r["status"] == PostStatus.PUBLISHED]
    failed = [r for r in results if r["status"] != PostStatus.PUBLISHED]

    st.markdown("### 📊 Publish Results")

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Published", len(success), delta=None)
    with col2:
        st.metric("Failed", len(failed), delta=None)
    with col3:
        rate = int(len(success) / len(results) * 100) if results else 0
        st.metric("Success Rate", f"{rate}%")

    # Success list
    if success:
        st.markdown("#### ✅ Successfully Published")
        for r in success:
            icon = PLATFORM_ICONS.get(r["platform"], "📱")
            url = r.get("url", "")
            link = f"[View post →]({url})" if url else ""
            st.markdown(
                f"<div class='success-card'>"
                f"{icon} <strong>{r['platform']}</strong> · ID: <code>{r['platform_post_id']}</code> · "
                f"{r.get('published_at', '')[:19].replace('T', ' ')} {link}"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Failed list
    if failed:
        st.markdown("#### ❌ Failed")
        for r in failed:
            st.error(
                f"{r['platform']} — {r.get('error', 'Unknown error')}"
            )

    # Start over
    st.markdown("---")
    col_new, _ = st.columns([1, 3])
    with col_new:
        if st.button("🔁 Start New Campaign", use_container_width=True):
            state.reset()
