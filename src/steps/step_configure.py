"""Step 0 – Configure: LLM provider, API key, brand settings, platforms."""

import streamlit as st
from src.state_manager import StateManager
from src.models import LLMProvider, Platform, Tone, PROVIDER_MODELS


def render_configure(state: StateManager):
    cfg = state.config

    st.markdown('<div class="section-title">⚙️ Configure Your Generator</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subtitle">Set up your AI provider, brand voice, and target platforms.</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1, 1], gap="large")

    # ── Left: LLM Config ──────────────────────────────────────────────────
    with col_left:
        st.markdown("#### 🤖 AI Provider")

        provider = st.selectbox(
            "LLM Provider",
            options=[LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GOOGLE],
            index=[LLMProvider.OPENAI, LLMProvider.ANTHROPIC, LLMProvider.GOOGLE].index(
                cfg.get("llm_provider", LLMProvider.OPENAI)
            ),
            help="Choose the AI provider to generate your posts.",
        )

        model_options = PROVIDER_MODELS.get(provider, [])
        current_model = cfg.get("model", model_options[0] if model_options else "")
        model_idx = model_options.index(current_model) if current_model in model_options else 0
        model = st.selectbox("Model", options=model_options, index=model_idx)

        api_key = st.text_input(
            "API Key",
            value=cfg.get("api_key", ""),
            type="password",
            placeholder="sk-... or your provider key",
            help="Your API key is stored only in your session and never sent anywhere else.",
        )

        key_labels = {
            LLMProvider.OPENAI: "Get your OpenAI key at platform.openai.com",
            LLMProvider.ANTHROPIC: "Get your Anthropic key at console.anthropic.com",
            LLMProvider.GOOGLE: "Get your Google AI key at aistudio.google.com",
        }
        st.caption(f"ℹ️ {key_labels.get(provider, '')}")

        st.markdown("---")
        st.markdown("#### 📊 Generation Settings")

        tone = st.selectbox(
            "Content Tone",
            options=[t.value for t in Tone],
            index=[t.value for t in Tone].index(cfg.get("tone", Tone.PROFESSIONAL)),
        )

        num_posts = st.slider(
            "Posts per topic per platform",
            min_value=1,
            max_value=5,
            value=cfg.get("num_posts", 3),
            help="How many post variants to generate for each topic.",
        )

    # ── Right: Brand + Platforms ───────────────────────────────────────────
    with col_right:
        st.markdown("#### 🏷️ Brand Identity")

        brand_name = st.text_input(
            "Brand / Product Name",
            value=cfg.get("brand_name", ""),
            placeholder="e.g. Acme Analytics",
        )

        brand_description = st.text_area(
            "Brand Description",
            value=cfg.get("brand_description", ""),
            placeholder="Describe your brand, product, target audience, and unique value proposition...",
            height=120,
        )

        st.markdown("---")
        st.markdown("#### 📱 Target Platforms")

        current_platforms = cfg.get("platforms", ["Twitter/X", "LinkedIn"])
        all_platforms = [p.value for p in Platform]

        platforms = st.multiselect(
            "Select Platforms",
            options=all_platforms,
            default=[p for p in current_platforms if p in all_platforms],
            help="Posts will be generated and optimised for each selected platform.",
        )

        if platforms:
            icons = {"Twitter/X": "🐦", "LinkedIn": "💼", "Instagram": "📸", "Facebook": "👥"}
            limits = {"Twitter/X": 280, "LinkedIn": 3000, "Instagram": 2200, "Facebook": 63206}
            cols = st.columns(len(platforms))
            for i, p in enumerate(platforms):
                with cols[i]:
                    st.markdown(
                        f"<div style='text-align:center; padding:8px; background:#f8fafc; "
                        f"border-radius:8px; border:1px solid #e2e8f0;'>"
                        f"<div style='font-size:1.5rem'>{icons.get(p,'')}</div>"
                        f"<div style='font-size:0.7rem; font-weight:600; color:#475569'>{p}</div>"
                        f"<div style='font-size:0.65rem; color:#94a3b8'>{limits.get(p,0):,} chars</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

    # ── Validation & Next ─────────────────────────────────────────────────
    st.markdown("---")
    col_btn, col_info = st.columns([1, 3])

    with col_btn:
        # Only block if no platform selected — API key is validated at generation time
        if st.button(
            "Save & Continue →",
            type="primary",
            use_container_width=True,
            disabled=not bool(platforms),
        ):
            state.update_config(
                llm_provider=provider,
                model=model,
                api_key=api_key,
                tone=tone,
                num_posts=num_posts,
                brand_name=brand_name,
                brand_description=brand_description,
                platforms=platforms,
            )
            state.next_step()

    with col_info:
        if not platforms:
            st.error("❌ Select at least one platform to continue.")
        elif not api_key:
            st.warning("⚠️ No API key entered — you can continue setting up, but generation will fail without one.")
        else:
            st.success("✅ Ready! Click **Save & Continue** to proceed.")
