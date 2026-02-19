

# main.py - FastAPI Backend
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

from submain import WorkflowBuilderOrchestrator

# Load node types
try:
    with open("node_types.json", "r", encoding="utf-8") as f:
        NODE_TYPES = json.load(f)
    print(f"✅ Loaded {len(NODE_TYPES)} node types")
except FileNotFoundError:
    print("⚠️  node_types.json not found, using empty list")
    NODE_TYPES = []

orchestrator: Optional[WorkflowBuilderOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables")

        orchestrator = WorkflowBuilderOrchestrator(
            api_key=api_key, node_types=NODE_TYPES
        )
        print("✅ Orchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {e}")
        raise

    yield

    orchestrator = None
    print("🔄 Orchestrator shutdown complete")


app = FastAPI(
    title="Workflow Builder API",
    description="AI-powered n8n workflow builder",
    version="1.0.0",
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
# Request / Response models
# ------------------------------------------------------------------

class WorkflowRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class WorkflowResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    response: str
    session_id: str


class HealthResponse(BaseModel):
    status: str
    message: str


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

        # Extract workflow - it's a SimpleWorkflow dataclass
        workflow = result.get("workflow_json")
        if workflow is None:
            nodes = []
            connections = {}
        else:
            nodes = [node.to_dict() for node in workflow.nodes]
            # Serialize connections: WorkflowConnection → dict
            connections = {}
            for node_name, conn_types in workflow.connections.items():
                connections[node_name] = {}
                for conn_type, conn_arrays in conn_types.items():
                    connections[node_name][conn_type] = [
                        [conn.to_dict() for conn in arr] for arr in conn_arrays
                    ]

        # Get last assistant message
        messages = result.get("messages", [])
        assistant_message = "Workflow built successfully"
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                assistant_message = msg.get("content", assistant_message)
                break
            elif hasattr(msg, "content") and getattr(msg, "type", "") == "ai":
                assistant_message = msg.content
                break

        return {
            "nodes": nodes,
            "connections": connections,
            "response": assistant_message,
            "session_id": request.session_id or "default",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error building workflow: {str(e)}"
        )


@app.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    return {"workflow_id": workflow_id, "message": "Workflow retrieval not yet implemented"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Workflow Builder API on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)