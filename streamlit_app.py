# streamlit_app.py
import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(
    page_title="Workflow Builder",
    page_icon="♾️",
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
        st.error("⭕ Cannot connect to API. Run: `python main.py`")
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out.")
    except Exception as e:
        st.error(f"⭕ {e}")
    return None


# ── Header ─────────────────────────────────────────────────────────
st.title(" AI Workflow Builder ♾️")
st.caption("Describe your workflow in plain English and get a structured automation workflow.")

# ── Sidebar ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Status")
    is_healthy = check_api()
    st.success(" ᯓ ✈︎ API Connected") if is_healthy else st.error("❌ API Disconnected")

    st.markdown("---")
    st.markdown("### 💡 Examples")
    for ex in [
        "Check weather API every hour and send an email if it rains",
        "Receive a webhook and post a Slack message",
        "Daily news update via HTTP and send to phone",
        "Create a complete n8n workflow JSON that sends daily weather updates to a phone via SMS only if weather is not normal   else  weather is normal so save the weather in excleshit with date and time",
        "Automate 3D body model generation from images using SAM-3D & Google Sheets",
    ]:
        st.caption(f"• {ex}")

# ── Chat History ───────────────────────────────────────────────────
if st.session_state.history:
    st.markdown("### 💬 Conversation")
    for msg in st.session_state.history:
        role = msg["role"]
        content = msg["content"]
        with st.chat_message(role):
            st.markdown(content)
    st.markdown("---")

# ── Input ──────────────────────────────────────────────────────────
user_input = st.text_area(
    "Describe your workflow:",
    placeholder="e.g. Every day at 8am fetch top news and send me an SMS",
    height=90,
)

if st.button(" Build Workflow", type="primary", use_container_width=False):
    if not user_input.strip():
        st.warning("Please enter a workflow description")
    elif not is_healthy:
        st.error("⭕ API not available")
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

# ── Results ────────────────────────────────────────────────────────
# Only show tabs if actual nodes exist (not on greeter/chat responses)
if st.session_state.workflow_state and st.session_state.workflow_state.get("nodes"):
    wf = st.session_state.workflow_state

    nodes = wf.get("nodes", [])
    edges = wf.get("edges", [])

    st.markdown("---")
    st.markdown(f"###  Workflow: **{wf.get('name', 'Untitled')}**")

    col1, col2 = st.columns(2)
    col1.metric("Nodes", len(nodes))
    col2.metric("Edges", len(edges))

    tab_nodes, tab_edges, tab_json = st.tabs(["🟦 Nodes", "🔗 Edges", "📄 Raw JSON"])

    # ── Nodes tab ──────────────────────────────────────────────────
    with tab_nodes:
        for node in nodes:
            node_id        = node.get("id", "")
            node_type      = node.get("type", "")
            node_type_acts = node.get("nodeTypeActions", "action")
            data           = node.get("data", {})
            label          = data.get("label", node_type)
            description    = data.get("description", "")
            action_id      = data.get("actionId", "")
            operation      = data.get("operation", "")
            resource       = data.get("resourceName", "")
            icon           = data.get("icon", "")

            type_emoji = {
                "trigger":     "⚡",
                "action":      "⚙️",
                "conditional": "🔀",
            }.get(node_type_acts, "📦")

            css_class = f"node-{node_type_acts}"

            st.markdown(f"""
<div class="node-card {css_class}">
  <strong>{type_emoji} {label} &nbsp;·&nbsp; <code>{node_id[:8]}…</code></strong><br>
  <small>
    Type: <b>{node_type}</b> &nbsp;|&nbsp;
    Role: <code>{node_type_acts}</code> &nbsp;|&nbsp;
    Operation: <code>{operation or '—'}</code> &nbsp;|&nbsp;
    Resource: <code>{resource or '—'}</code>
  </small>
  {"<br><small>" + description + "</small>" if description else ""}
</div>
""", unsafe_allow_html=True)

            with st.expander(f"Parameters — {label}"):
                st.json(node.get("parameters", {}))

    # ── Edges tab ──────────────────────────────────────────────────
    with tab_edges:
        if edges:
            # Build id → label lookup using new format
            id_to_label = {
                n["id"]: n.get("data", {}).get("label", n["id"][:8])
                for n in nodes
            }
            for edge in edges:
                src       = edge.get("source", "")
                tgt       = edge.get("target", "")
                src_label = id_to_label.get(src, src[:8] if src else "?")
                tgt_label = id_to_label.get(tgt, tgt[:8] if tgt else "?")
                edge_type = edge.get("type", "action")
                st.markdown(f"""
<div class="edge-card">
  ⚡ <b>{src_label}</b> &nbsp;→&nbsp; <b>{tgt_label}</b>
  <br><small>type: <code>{edge_type}</code> &nbsp;|&nbsp; <code>{src[:8]}…</code> → <code>{tgt[:8]}…</code></small>
</div>
""", unsafe_allow_html=True)
        else:
            st.info("No edges found")

    # ── JSON tab ───────────────────────────────────────────────────
    with tab_json:
        clean = {
            "id":       wf.get("id", 1),
            "name":     wf.get("name"),
            "nodes":    nodes,
            "edges":    edges,
            "viewport": wf.get("viewport", {"x": 0, "y": 0, "zoom": 1}),
            "publish":  wf.get("publish", 0),
        }
        st.json(clean)
        st.download_button(
            "⬇️ Download JSON",
            data=json.dumps(clean, indent=2),
            file_name=f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

st.markdown("---")
st.caption("")