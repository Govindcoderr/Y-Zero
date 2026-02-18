# # streamlit_app.py - Streamlit Frontend
# import streamlit as st
# import requests
# import json
# from datetime import datetime
# import time

# # Page configuration
# st.set_page_config(
#     page_title="Workflow Builder",
#     page_icon="🤖",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS
# st.markdown("""
#     <style>
#     .main {
#         padding: 2rem;
#     }
#     .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
#         font-size: 1.1rem;
#     }
#     .node-card {
#         background-color: #f0f2f6;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         margin: 0.5rem 0;
#         border-left: 4px solid #1f77e5;
#     }
#     .connection-card {
#         background-color: #e8f4f8;
#         padding: 0.75rem;
#         border-radius: 0.5rem;
#         margin: 0.3rem 0;
#         font-size: 0.9rem;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # API Configuration
# API_BASE_URL = st.secrets.get("API_URL", "http://localhost:8000")

# # Session state
# if "workflow_state" not in st.session_state:
#     st.session_state.workflow_state = None
# if "conversation_history" not in st.session_state:
#     st.session_state.conversation_history = []
# if "api_status" not in st.session_state:
#     st.session_state.api_status = None

# def check_api_health():
#     """Check if API is available"""
#     try:
#         response = requests.get(f"{API_BASE_URL}/health", timeout=2)
#         return response.status_code == 200
#     except:
#         return False

# def build_workflow(message: str):
#     """Call API to build workflow"""
#     try:
#         response = requests.post(
#             f"{API_BASE_URL}/workflow",
#             json={"message": message},
#             timeout=30
#         )
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.ConnectionError:
#         st.error("❌ Cannot connect to API. Make sure the FastAPI server is running on http://localhost:8000")
#         return None
#     except requests.exceptions.Timeout:
#         st.error("⏱️ API request timed out. Please try again.")
#         return None
#     except Exception as e:
#         st.error(f"❌ Error: {str(e)}")
#         return None

# def get_node_types():
#     """Get available node types"""
#     try:
#         response = requests.get(f"{API_BASE_URL}/node-types", timeout=5)
#         response.raise_for_status()
#         return response.json()
#     except:
#         return {"node_types": [], "count": 0}

# # Header
# st.title("🤖 AI Workflow Builder")
# st.markdown("Build n8n workflows using natural language powered by LLM")

# # Sidebar
# with st.sidebar:
#     st.markdown("### ⚙️ Configuration")
    
#     # API Status
#     is_api_healthy = check_api_health()
#     if is_api_healthy:
#         st.success("✅ API Connected")
#     else:
#         st.error("❌ API Disconnected")
#         st.info("Start the API server with: `python main.py`")
    
#     # API URL Configuration
#     custom_api_url = st.text_input(
#         "API URL",
#         value=API_BASE_URL,
#         help="FastAPI server URL"
#     )
#     if custom_api_url != API_BASE_URL:
#         API_BASE_URL = custom_api_url
    
#     st.markdown("---")
#     st.markdown("### 📚 Available Nodes")
    
#     node_info = get_node_types()
#     if node_info["count"] > 0:
#         st.metric("Total Node Types", node_info["count"])
#         with st.expander("View All Nodes"):
#             for node in node_info["node_types"][:10]:
#                 st.write(f"• **{node.get('displayName', node.get('name'))}**")
#                 st.caption(node.get('description', 'No description'))
#     else:
#         st.warning("No node types available")
    
#     st.markdown("---")
#     st.markdown("### 💡 Example Prompts")
#     examples = [
#         "Create a workflow that checks weather API every hour",
#         "Build a workflow to scrape data and send emails",
#         "Create a workflow that processes incoming webhooks",
#     ]
#     for example in examples:
#         st.caption(f"• {example}")

# # Main content area
# st.markdown("### 🏗️ Workflow Builder")

# # Input area
# col1, col2 = st.columns([4, 1])
# with col1:
#     user_input = st.text_input(
#         "Describe your workflow:",
#         placeholder="e.g., Create a workflow that checks weather API every hour and sends me an email",
#         label_visibility="collapsed"
#     )

# with col2:
#     build_button = st.button("Build", use_container_width=True, type="primary")

# # Process input
# if build_button and user_input:
#     if not is_api_healthy:
#         st.error("❌ API is not available. Please start the FastAPI server.")
#     else:
#         with st.spinner("🔄 Building your workflow..."):
#             result = build_workflow(user_input)
            
#             if result:
#                 st.session_state.workflow_state = result
#                 st.session_state.conversation_history.append({
#                     "role": "user",
#                     "content": user_input,
#                     "timestamp": datetime.now()
#                 })
#                 st.session_state.conversation_history.append({
#                     "role": "assistant",
#                     "content": result["response"],
#                     "timestamp": datetime.now()
#                 })
#                 st.success("✅ Workflow built successfully!")

# # Display tabs
# if st.session_state.workflow_state:
#     tab1, tab2, tab3, tab4 = st.tabs(["📊 Workflow", "🔗 Connections", "💬 Chat", "📋 JSON"])
    
#     with tab1:
#         st.markdown("### Nodes Added")
#         nodes = st.session_state.workflow_state.get("nodes", [])
        
#         if nodes:
#             for i, node in enumerate(nodes, 1):
#                 with st.container():
#                     col1, col2 = st.columns([3, 1])
#                     with col1:
#                         st.markdown(f"**{i}. {node.get('name', 'Unknown')}**")
#                         st.caption(f"Type: {node.get('type', 'N/A')}")
#                     with col2:
#                         st.write(f"ID: `{node.get('id', 'N/A')}`")
            
#             st.metric("Total Nodes", len(nodes))
#         else:
#             st.info("No nodes in workflow yet")
    
#     with tab2:
#         st.markdown("### Workflow Connections")
#         connections = st.session_state.workflow_state.get("connections", {})
        
#         if connections:
#             for source, targets in connections.items():
#                 with st.expander(f"From: {source}"):
#                     if isinstance(targets, dict):
#                         for conn_type, conns in targets.items():
#                             st.write(f"**{conn_type}**")
#                             st.json(conns)
#                     else:
#                         st.json(targets)
#         else:
#             st.info("No connections in workflow yet")
    
#     with tab3:
#         st.markdown("### 💬 Conversation")
        
#         for msg in st.session_state.conversation_history:
#             with st.chat_message(msg["role"]):
#                 st.write(msg["content"])
#                 st.caption(msg["timestamp"].strftime("%H:%M:%S"))
        
#         # Follow-up input
#         follow_up = st.text_input(
#             "Ask follow-up questions or modify the workflow:",
#             placeholder="e.g., Add error handling, Change the schedule interval...",
#             label_visibility="collapsed"
#         )
        
#         if follow_up:
#             if st.button("Send", key="follow_up_button"):
#                 if not is_api_healthy:
#                     st.error("❌ API is not available")
#                 else:
#                     with st.spinner("Processing..."):
#                         result = build_workflow(follow_up)
#                         if result:
#                             st.session_state.workflow_state = result
#                             st.session_state.conversation_history.append({
#                                 "role": "user",
#                                 "content": follow_up,
#                                 "timestamp": datetime.now()
#                             })
#                             st.session_state.conversation_history.append({
#                                 "role": "assistant",
#                                 "content": result["response"],
#                                 "timestamp": datetime.now()
#                             })
#                             st.rerun()
    
#     with tab4:
#         st.markdown("### 📋 Raw JSON")
#         st.json(st.session_state.workflow_state)
        
#         # Download button
#         workflow_json = json.dumps(st.session_state.workflow_state, indent=2)
#         st.download_button(
#             label="⬇️ Download Workflow JSON",
#             data=workflow_json,
#             file_name=f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
#             mime="application/json"
#         )
# else:
#     st.info("👈 Start by describing your workflow in the text input above")

# # Footer
# st.markdown("---")
# st.markdown(
#     """
#     <div style='text-align: center; color: gray; font-size: 0.9rem;'>
#     🚀 Workflow Builder v1.0 | Powered by LLM & n8n
#     </div>
#     """,
#     unsafe_allow_html=True
# )




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
            timeout=90
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