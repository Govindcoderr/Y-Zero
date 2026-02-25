
# streamlit_app.py
import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(
    page_title="Workflow Builder",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


API_BASE_URL = "http://localhost:8000"

if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = None
if "history" not in st.session_state:
    st.session_state.history = []


def check_api():
    try:
        return requests.get(f"{API_BASE_URL}/health", timeout=3).status_code == 200
    except:
        return False


def build_workflow(message: str):
    try:
        r = requests.post(f"{API_BASE_URL}/workflow", json={"message": message}, timeout=360, stream=True)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Run: `python main.py`")
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out.")
    except Exception as e:
        st.error(f"❌ {e}")
    return None


# ── Header ────────────────────────────────────────────────────────
st.title("🤖 AI Workflow Builder")
st.caption("Describe your workflow in plain English and get a structured automation workflow.")

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Status")
    is_healthy = check_api()
    st.success("✅ API Connected") if is_healthy else st.error("❌ API Disconnected")

    st.markdown("---")
    st.markdown("### 💡 Examples")
    for ex in [
        "Check weather API every hour and send an email if it rains",
        "Receive a webhook and post a Slack message",
        "Daily news update via HTTP and send to phone",
    ]:
        st.caption(f"• {ex}")

# ── Input ─────────────────────────────────────────────────────────
user_input = st.text_area(
    "Describe your workflow:",
    placeholder="e.g. Every day at 8am fetch top news and send me an SMS",
    height=90,
)

if st.button(" Build Workflow", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Please enter a workflow description")
    elif not is_healthy:
        st.error("❌ API not available")
    else:
        with st.spinner("🔄 Building workflow…"):
            result = build_workflow(user_input)
            if result:
                st.session_state.workflow_state = result
                st.session_state.history.append(
                    {"role": "user", "content": user_input, "ts": datetime.now()}
                )
                st.session_state.history.append(
                    {"role": "assistant", "content": result.get("response", "Done"), "ts": datetime.now()}
                )
                st.success(" Workflow built!")
                st.rerun()

# ── Results ───────────────────────────────────────────────────────
if st.session_state.workflow_state:
    wf = st.session_state.workflow_state
    nodes = wf.get("nodes", [])
    edges = wf.get("edges", [])

    st.markdown("---")
    st.markdown(f"###  Workflow: **{wf.get('name', 'Untitled')}**")

    col1, col2 = st.columns(2)
    col1.metric("Nodes", len(nodes))
    col2.metric("Edges", len(edges))

    tab_nodes, tab_edges, tab_json = st.tabs(["🟦 Nodes", "🔗 Edges", "📄 Raw JSON"])

    # ── Nodes tab ────────────────────────────────────────────────
    with tab_nodes:
        for node in nodes:
            node_type = node.get("type", "action")
            css_class = f"node-{node_type}"
            type_emoji = {"trigger": "⚡", "action": "⚙️", "condition": "🔀"}.get(node_type, "📦")
            st.markdown(f"""
<div class="node-card {css_class}">
  <strong>{type_emoji} {node.get('value')} &nbsp;·&nbsp; <code>{node.get('nodeId','')[:8]}…</code></strong><br>
  <small>Type: <b>{node_type}</b> &nbsp;|&nbsp; expressionExecutionName: <code>{node.get('expressionExecutionName')}</code></small>
</div>
""", unsafe_allow_html=True)
            with st.expander(f"Parameters — {node.get('value')}"):
                st.json(node.get("parameters", {}))

    # ── Edges tab ─────────────────────────────────────────────────
    with tab_edges:
        if edges:
            # Build id→value lookup for display
            id_to_value = {n["nodeId"]: n["value"] for n in nodes}
            for edge in edges:
                src = edge.get("from_node", "")
                tgt = edge.get("to_node", "")
                src_label = id_to_value.get(src, src[:8])
                tgt_label = id_to_value.get(tgt, tgt[:8])
                st.markdown(f"""
<div class="edge-card">
  ⚡ <b>{src_label}</b> &nbsp;→&nbsp; <b>{tgt_label}</b>
  <br><small><code>{src}</code> → <code>{tgt}</code></small>
</div>
""", unsafe_allow_html=True)
        else:
            st.info("No edges found")

    # ── JSON tab ──────────────────────────────────────────────────
    with tab_json:
        clean = {"name": wf.get("name"), "nodes": nodes, "edges": edges}
        st.json(clean)
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(clean, indent=2),
            file_name=f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

st.markdown("---")
st.caption("")