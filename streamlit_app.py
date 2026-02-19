

# streamlit_app.py - Streamlit Frontend
import streamlit as st
import requests
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Workflow Builder",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
    }
    </style>
""", unsafe_allow_html=True)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Session state initialization
if "workflow_state" not in st.session_state:
    st.session_state.workflow_state = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

def check_api_health():
    """Check if API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def build_workflow(message: str):
    """Call API to build workflow"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/workflow",
            json={"message": message},
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Start server: `python main.py`")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Try a simpler workflow.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None

def get_node_types():
    """Get available node types"""
    try:
        response = requests.get(f"{API_BASE_URL}/node-types", timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        return {"node_types": [], "count": 0}

# Header
st.title("🤖 AI Workflow Builder")
st.markdown("Build n8n workflows using natural language")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Status")
    
    is_api_healthy = check_api_health()
    if is_api_healthy:
        st.success("✅ API Connected")
    else:
        st.error("❌ API Disconnected")
        st.code("python main.py", language="bash")
    
    st.markdown("---")
    st.markdown("### 💡 Examples")
    examples = [
        "Create a workflow that checks weather API every hour",
        "Build a workflow to scrape data and send emails",
        "Create a workflow for processing webhooks",
    ]
    for example in examples:
        st.caption(f"• {example}")

# Main content
st.markdown("### 🏗️ Describe Your Workflow")

user_input = st.text_area(
    "What do you want to build?",
    placeholder="e.g., Create a workflow that checks weather API every hour...",
    height=100
)

if st.button("🚀 Build Workflow", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("Please enter a workflow description")
    elif not is_api_healthy:
        st.error("❌ API is not available. Start the server first.")
    else:
        with st.spinner("🔄 Building your workflow..."):
            result = build_workflow(user_input)
            
            if result:
                st.session_state.workflow_state = result
                st.session_state.conversation_history.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now()
                })
                st.session_state.conversation_history.append({
                    "role": "assistant",
                    "content": result.get("response", "Done"),
                    "timestamp": datetime.now()
                })
                st.success("✅ Workflow built!")
                st.rerun()

# Display results
if st.session_state.workflow_state:
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📊 Nodes", "🔗 Connections", "📋 JSON"])
    
    with tab1:
        nodes = st.session_state.workflow_state.get("nodes", [])
        if nodes:
            for i, node in enumerate(nodes, 1):
                st.markdown(f"**{i}. {node.get('name', 'Unknown')}**")
                st.caption(f"Type: `{node.get('type', 'N/A')}`")
                st.caption(f"ID: `{node.get('id', 'N/A')[:8]}...`")
                st.markdown("---")
            st.metric("Total Nodes", len(nodes))
        else:
            st.info("No nodes yet")
    
    with tab2:
        connections = st.session_state.workflow_state.get("connections", {})
        if connections:
            st.json(connections)
        else:
            st.info("No connections yet")
    
    with tab3:
        st.json(st.session_state.workflow_state)
        
        workflow_json = json.dumps(st.session_state.workflow_state, indent=2)
        st.download_button(
            "⬇️ Download JSON",
            data=workflow_json,
            file_name=f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# Footer
st.markdown("---")
st.caption("🚀 Workflow Builder v1.0 | Powered by Groq")