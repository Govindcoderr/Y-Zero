

# # main.py - FastAPI Backend
# from fastapi import FastAPI, HTTPException, WebSocket
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import Optional, List, Dict, Any
# import json
# import os
# from dotenv import load_dotenv
# from contextlib import asynccontextmanager

# load_dotenv()

# from submain import WorkflowBuilderOrchestrator

# # Load node types
# try:
#     with open("node_types.json", "r", encoding="utf-8") as f:
#         NODE_TYPES = json.load(f)
#     print(f"✅ Loaded {len(NODE_TYPES)} node types")
# except FileNotFoundError:
#     print("⚠️  node_types.json not found, using empty list")
#     NODE_TYPES = []

# orchestrator: Optional[WorkflowBuilderOrchestrator] = None


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     global orchestrator
#     try:
#         api_key = os.getenv("GROQ_API_KEY")
#         if not api_key:
#             raise ValueError("GROQ_API_KEY not set in environment variables")

#         orchestrator = WorkflowBuilderOrchestrator(
#             api_key=api_key, node_types=NODE_TYPES
#         )
#         print("✅ Orchestrator initialized successfully")
#     except Exception as e:
#         print(f"❌ Failed to initialize orchestrator: {e}")
#         raise

#     yield

#     orchestrator = None
#     print("🔄 Orchestrator shutdown complete")


# app = FastAPI(
#     title="Workflow Builder API",
#     description="AI-powered n8n workflow builder",
#     version="1.0.0",
#     lifespan=lifespan,
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ------------------------------------------------------------------
# # Request / Response models
# # ------------------------------------------------------------------

# class WorkflowRequest(BaseModel):
#     message: str
#     session_id: Optional[str] = None


# class WorkflowResponse(BaseModel):
#     nodes: List[Dict[str, Any]]
#     connections: Dict[str, Any]
#     response: str
#     session_id: str


# class HealthResponse(BaseModel):
#     status: str
#     message: str


# # ------------------------------------------------------------------
# # Routes
# # ------------------------------------------------------------------

# @app.get("/health", response_model=HealthResponse)
# async def health_check():
#     return {"status": "healthy", "message": "Workflow Builder API is running"}


# @app.get("/node-types")
# async def get_node_types():
#     return {"node_types": NODE_TYPES[:20], "count": len(NODE_TYPES)}


# @app.post("/workflow", response_model=WorkflowResponse)
# async def build_workflow(request: WorkflowRequest):
#     if not orchestrator:
#         raise HTTPException(status_code=503, detail="Orchestrator not initialized")

#     if not request.message.strip():
#         raise HTTPException(status_code=400, detail="Message cannot be empty")

#     try:
#         result = await orchestrator.process_message(request.message)

#         # Extract workflow - it's a SimpleWorkflow dataclass
#         workflow = result.get("workflow_json")
#         if workflow is None:
#             nodes = []
#             connections = {}
#         else:
#             nodes = [node.to_dict() for node in workflow.nodes]
#             # Serialize connections: WorkflowConnection → dict
#             connections = {}
#             for node_name, conn_types in workflow.connections.items():
#                 connections[node_name] = {}
#                 for conn_type, conn_arrays in conn_types.items():
#                     connections[node_name][conn_type] = [
#                         [conn.to_dict() for conn in arr] for arr in conn_arrays
#                     ]

#         # Get last assistant message
#         messages = result.get("messages", [])
#         assistant_message = "Workflow built successfully"
#         for msg in reversed(messages):
#             if isinstance(msg, dict) and msg.get("role") == "assistant":
#                 assistant_message = msg.get("content", assistant_message)
#                 break
#             elif hasattr(msg, "content") and getattr(msg, "type", "") == "ai":
#                 assistant_message = msg.content
#                 break

#         return {
#             "nodes": nodes,
#             "connections": connections,
#             "response": assistant_message,
#             "session_id": request.session_id or "default",
#         }

#     except Exception as e:
#         import traceback
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500, detail=f"Error building workflow: {str(e)}"
#         )


# @app.get("/workflow/{workflow_id}")
# async def get_workflow(workflow_id: str):
#     return {"workflow_id": workflow_id, "message": "Workflow retrieval not yet implemented"}


# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting Workflow Builder API on http://localhost:8000")
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)



# main.py - FastAPI Backend
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import httpx
from backend.utils.node_loader import fetch_nodes_from_api
from backend.utils.node_normalizer import load_and_normalize_nodes


load_dotenv()

from submain import WorkflowBuilderOrchestrator

# # Load node types
# try:
#     with open("node_types.json", "r", encoding="utf-8") as f:
#         NODE_TYPES = json.load(f)
#     print(f"✅ Loaded {len(NODE_TYPES)} node types")
# except FileNotFoundError:
#     print("⚠️  node_types.json not found, using empty list")
#     NODE_TYPES = []

# BAAD MEIN (naya code):
# from backend.utils.node_normalizer import load_and_normalize_nodes

# NODE_TYPES = load_and_normalize_nodes()
# print(f"✅ Loaded {len(NODE_TYPES)} node types")




orchestrator: Optional[WorkflowBuilderOrchestrator] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator

        # Nodes load karo — API first, local file fallback
    nodes_api_url = os.getenv("NODES_API_URL", "").strip()

    if nodes_api_url:
        NODE_TYPES = await fetch_nodes_from_api(nodes_api_url)
        if not NODE_TYPES:
            print("⚠️  API returned 0 nodes — falling back to local file")
            NODE_TYPES = load_and_normalize_nodes()
    else:
        NODE_TYPES = load_and_normalize_nodes()

    if not NODE_TYPES:
        print("⚠️  WARNING: No nodes loaded. Set NODES_API_URL in .env")

    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables")
        orchestrator = WorkflowBuilderOrchestrator(api_key=api_key, node_types=NODE_TYPES)
        print("✅ Orchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {e}")
        raise
    yield
    orchestrator = None
    print("🔄 Orchestrator shutdown complete")


app = FastAPI(
    title="Workflow Builder API",
    description="AI-powered workflow builder",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Pydantic models
# ------------------------------------------------------------------

class WorkflowRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class HandleBoundItem(BaseModel):
    id: str
    type: str
    nodeId: str
    position: str
    x: float
    y: float
    width: int
    height: int


class HandleBounds(BaseModel):
    source: List[HandleBoundItem]
    target: Optional[List[HandleBoundItem]] = None


class NodeData(BaseModel):
    icon: str
    color: str
    label: str
    value: Dict[str, Any]
    actionId: str
    operation: Optional[str] = None
    description: str
    resourceName: Optional[str] = None


class NodeOut(BaseModel):
    id: str
    type: str
    dimensions: Dict[str, Any]
    computedPosition: Dict[str, Any]
    handleBounds: HandleBounds
    selectable: bool
    selected: bool
    dragging: bool
    resizing: bool
    initialized: bool
    isParent: bool
    position: Dict[str, Any]
    data: NodeData
    events: Dict[str, Any]
    parameters: Dict[str, Any]
    nodeTypeActions: Optional[str] = None


class EdgeOut(BaseModel):
    id: str
    type: str
    source: str
    target: str
    sourceHandle: str
    targetHandle: str


class WorkflowResponse(BaseModel):
    id: int
    name: str
    nodes: List[NodeOut]
    edges: List[EdgeOut]
    viewport: Dict[str, Any]
    publish: int
    response: str
    session_id: str

class HealthResponse(BaseModel):
    status: str
    message: str


# Helper: extract last assistant message from LangGraph state   

def extract_assistant_message(result: dict, fallback: str = "Done") -> str:
    """
    Robustly extract the last assistant/AI message from LangGraph state.

    LangGraph's add_messages reducer can store messages as:
      - dict:       {"role": "assistant", "content": "..."}
      - AIMessage:  msg.type == "ai", msg.content == "..."
      - HumanMessage, SystemMessage (skip these)
    
    We walk the list in reverse and return the first assistant reply found.
    """
    messages = result.get("messages", [])

    for msg in reversed(messages):
        # ── dict format ───────────────────────────────────────────
        if isinstance(msg, dict):
            role = msg.get("role", "")
            if role in ("assistant", "ai"):
                content = msg.get("content", "").strip()
                if content:
                    return content

        # ── LangChain message object format ───────────────────────
        else:
            msg_type = getattr(msg, "type", "")
            if msg_type in ("ai", "assistant"):
                content = getattr(msg, "content", "").strip()
                if content:
                    return content

    return fallback


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "healthy", "message": "Workflow Builder API is running"}


@app.get("/node-types")
async def get_node_types():
    return {"node_types": NODE_TYPES[:20], "count": len(NODE_TYPES)}


@app.post("/workflow", response_model=WorkflowResponse)
async def build_workflow(request: WorkflowRequest):
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = await orchestrator.process_message(request.message)


        # ── Check if greeter short-circuited the pipeline ──────────
        greeter_proceed = result.get("greeter_proceed", True)

        if not greeter_proceed:
            # Greeter handled it — no workflow built, just return the reply
            reply = extract_assistant_message(result, fallback="Hello! How can I help you?")
            print(f"🤝 Greeter response returned to frontend: {reply[:80]}...")
            return {
                "id":         1,
                "name":       "Chat",
                "nodes":      [],
                "edges":      [],
                "viewport":   {"x": 0, "y": 0, "zoom": 1},
                "publish":    0,
                "response":   reply,
                "session_id": request.session_id or "default",
            }

        # Get the SimpleWorkflow object from state
        workflow = result.get("workflow_json")
        if workflow is None:
            raise ValueError("No workflow returned from orchestrator")

        # Produce the output-format dict
        # to_output_dict() returns {name, nodes, edges}
        # to_dict() is the old internal format - do NOT use it here
        if hasattr(workflow, 'to_output_dict'):
            output = workflow.to_output_dict()
        else:
            # Fallback: if an old workflow object somehow got in, wrap it safely
            output = {"name": getattr(workflow, 'name', 'Workflow'), "nodes": [], "edges": []}

        # Get last assistant message
        # assistant_message = "Workflow built successfully"
        # for msg in reversed(result.get("messages", [])):
        #     if isinstance(msg, dict) and msg.get("role") == "assistant":
        #         assistant_message = msg.get("content", assistant_message)
        #         break
        #     elif hasattr(msg, "content") and getattr(msg, "type", "") == "ai":
        #         assistant_message = msg.content
        #         break

        assistant_message = extract_assistant_message(
            result, fallback="✅ Workflow built successfully"
        )

        return {
            "id":         output.get("id", 1),
            "name":       output["name"],
            "nodes":      output["nodes"],
            "edges":      output["edges"],
            "viewport":   output.get("viewport", {"x": 0, "y": 0, "zoom": 1}),
            "publish":    output.get("publish", 0),
            "response":   assistant_message,
            "session_id": request.session_id or "default",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error building workflow: {str(e)}")

from backend.utils.Workflow_trans import transform_workflow

@app.post("/workflow/publish")
def publish_workflow(data: dict):
    frontend_json = transform_workflow(data, workflow_id=data.get("id", 0))
    return frontend_json

@app.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    return {"workflow_id": workflow_id, "message": "Workflow retrieval not yet implemented"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Workflow Builder API on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)