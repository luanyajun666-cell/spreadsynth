from __future__ import annotations

import time
from datetime import datetime

import requests
import streamlit as st

BACKEND_URL = "http://backend:8000"

st.set_page_config(page_title="SpreadSynth Demo", page_icon="⚡", layout="wide")

st.title("SpreadSynth ⚡ Cyber Radar Demo")
st.caption("Real-time spread intelligence with red-alert battle report mode")

col_a, col_b = st.columns([2, 1])

entity = st.sidebar.text_input("Entity", value="mcp-agent")
wow_mode = st.sidebar.toggle("Force WOW mode", value=True)

if st.sidebar.button("Refresh Signal"):
    st.rerun()

with col_a:
    st.subheader("Radar Core")
    try:
        resp = requests.get(f"{BACKEND_URL}/api/demo/opportunity", params={"entity": entity, "wow": wow_mode}, timeout=15)
        data = resp.json()
    except Exception as exc:
        st.error(f"Backend unavailable: {exc}")
        st.stop()

    score = data["score"]["score"]
    trigger = data["score"]["trigger"]

    if score >= 90:
        st.error(f"RED ALERT • Score {score}")
    elif score >= 75:
        st.warning(f"EXECUTE NOW • Score {score}")
    else:
        st.info(f"WATCH • Score {score}")

    st.progress(min(max(score / 100.0, 0.0), 1.0), text=f"SpreadScore {score}/100")
    st.json(data["score"])

with col_b:
    st.subheader("Action Queue")
    st.write("- Alert router")
    st.write("- Battle report generator")
    st.write("- Telegram notifier")

if score >= 90:
    st.markdown("---")
    st.subheader("🚨 WOW Mode: Battle Report + Telegram Push")

    summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entity": entity,
        "score": score,
        "trigger": trigger,
        "recommendation": "Execute within 20 minutes window",
        "next_action": "Publish localized insight thread + notify operator",
    }

    st.code(
        "\n".join(
            [
                f"[BATTLE REPORT] {summary['timestamp']}",
                f"Entity: {summary['entity']}",
                f"Score: {summary['score']} ({summary['trigger']})",
                f"Recommendation: {summary['recommendation']}",
                f"Next Action: {summary['next_action']}",
            ]
        )
    )

    holder = st.empty()
    frames = [
        "[Telegram] Connecting secure channel...",
        "[Telegram] Uploading battle report payload...",
        "[Telegram] Rendering neon alert card...",
        "[Telegram] ✅ Sent to @SpreadOpsChannel",
    ]
    for frame in frames:
        holder.info(frame)
        time.sleep(0.45)

st.markdown("---")
st.caption("Demo build for launch. Replace with ECharts/Three.js production frontend later.")
