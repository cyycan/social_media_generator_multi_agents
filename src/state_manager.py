"""Centralized session state management."""

import streamlit as st
from typing import Any, Optional


class StateManager:
    """Single source of truth for all wizard state."""

    DEFAULTS: dict[str, Any] = {
        "current_step": 0,
        # Step 0 – Configure
        "config": {
            "llm_provider": "OpenAI",
            "api_key": "",
            "model": "gpt-4o-mini",
            "platforms": ["Twitter/X", "LinkedIn"],
            "tone": "Professional",
            "brand_name": "",
            "brand_description": "",
            "num_posts": 3,
        },
        # Step 1 – Upload
        "sample_data": {
            "topics": [],
            "keywords": [],
            "extra_context": "",
            "raw_text": "",
        },
        # Step 2 – Review
        "generated_posts": [],   # list[GeneratedPost dict]
        "posts_generated": False,
        # Step 3 – Publish
        "publish_results": [],
    }

    def __init__(self):
        for key, value in self.DEFAULTS.items():
            if key not in st.session_state:
                st.session_state[key] = value

    # ── Generic helpers ────────────────────────────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        return st.session_state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        st.session_state[key] = value

    # ── Step navigation ────────────────────────────────────────────────────
    @property
    def current_step(self) -> int:
        return st.session_state["current_step"]

    def next_step(self) -> None:
        if st.session_state["current_step"] < 3:
            st.session_state["current_step"] += 1
            st.rerun()

    def prev_step(self) -> None:
        if st.session_state["current_step"] > 0:
            st.session_state["current_step"] -= 1
            st.rerun()

    def go_to(self, step: int) -> None:
        st.session_state["current_step"] = step
        st.rerun()

    # ── Config ─────────────────────────────────────────────────────────────
    @property
    def config(self) -> dict:
        return st.session_state["config"]

    def update_config(self, **kwargs) -> None:
        st.session_state["config"].update(kwargs)

    # ── Sample data ────────────────────────────────────────────────────────
    @property
    def sample_data(self) -> dict:
        return st.session_state["sample_data"]

    def update_sample_data(self, **kwargs) -> None:
        st.session_state["sample_data"].update(kwargs)

    # ── Generated posts ────────────────────────────────────────────────────
    @property
    def generated_posts(self) -> list:
        return st.session_state["generated_posts"]

    def set_generated_posts(self, posts: list) -> None:
        st.session_state["generated_posts"] = posts
        st.session_state["posts_generated"] = True

    def update_post(self, post_id: str, **kwargs) -> None:
        for i, post in enumerate(st.session_state["generated_posts"]):
            if post["id"] == post_id:
                st.session_state["generated_posts"][i].update(kwargs)
                break

    @property
    def posts_generated(self) -> bool:
        return st.session_state.get("posts_generated", False)

    # ── Publish results ────────────────────────────────────────────────────
    @property
    def publish_results(self) -> list:
        return st.session_state["publish_results"]

    def add_publish_result(self, result: dict) -> None:
        st.session_state["publish_results"].append(result)

    def reset(self) -> None:
        for key, value in self.DEFAULTS.items():
            import copy
            st.session_state[key] = copy.deepcopy(value)
        st.rerun()
