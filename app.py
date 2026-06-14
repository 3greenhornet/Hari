"""Streamlit web app for interacting with Hari."""

from __future__ import annotations

import json
from typing import Any, Dict, List

import streamlit as st

import engine


st.set_page_config(page_title="Hari Core", page_icon="🧠", layout="centered")


def _init_session_state() -> None:
    """Initialize session containers once."""
    if "chat_feed" not in st.session_state:
        st.session_state.chat_feed = []


def _render_message_feed(chat_feed: List[Dict[str, Any]]) -> None:
    """Render structured conversation feed."""
    for event in chat_feed:
        role = event.get("role", "assistant")
        message = event.get("message", "")
        with st.chat_message(role):
            if role == "assistant":
                st.markdown(
                    """
                    <div style="
                        background: #111827;
                        color: #f9fafb;
                        border: 1px solid #374151;
                        border-radius: 10px;
                        padding: 14px;
                        margin-bottom: 8px;
                        line-height: 1.5;
                    ">
                    """
                    + message
                    + """
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                monologue = event.get("monologue_json")
                if monologue:
                    with st.expander("🔍 Cognitive Core Processing (Hidden JSON)"):
                        st.markdown(
                            """
                            <div style="
                                background: #f3f4f6;
                                color: #374151;
                                border: 1px solid #d1d5db;
                                border-radius: 8px;
                                padding: 8px;
                            ">
                            """,
                            unsafe_allow_html=True,
                        )
                        st.code(
                            json.dumps(monologue, indent=2, ensure_ascii=False),
                            language="json",
                        )
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(message)


def _handle_user_message(user_input: str) -> None:
    """Process one user message and append both sides to feed."""
    st.session_state.chat_feed.append({"role": "user", "message": user_input})

    with st.status("Hari is running autonomous internal monologues...", expanded=False):
        result = engine.generate_hari_response(user_input)

    st.session_state.chat_feed.append(
        {
            "role": "assistant",
            "message": result["dialogue"],
            "monologue_json": result["monologue_json"],
            "metrics": result.get("metrics", {}),
            "flow_guard": result.get("flow_guard", "CONTINUOUS"),
        }
    )


def main() -> None:
    """Run app layout and interaction loop."""
    _init_session_state()

    st.title("Hari Core Interface")
    st.caption("Autonomous two-step generation with visible dialogue + hidden cognition.")

    _render_message_feed(st.session_state.chat_feed)

    user_input = st.chat_input("Type your message to Hari...")
    if user_input:
        try:
            _handle_user_message(user_input)
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Request failed: {exc}")


if __name__ == "__main__":
    main()
