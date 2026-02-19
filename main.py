# # main.py - FastAPI Backend
# from fastapi import FastAPI, HTTPException, WebSocket
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import Optional, List, Dict, Any
# import json
# import asyncio
# from main import WorkflowBuilderOrchestrator
# from contextlib import asynccontextmanager

# # Load node types
# with open("node_types.json", "r") as f:
#     NODE_TYPES = json.load(f)

# # Global orchestrator instance
# orchestrator = None

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Lifespan context manager for app startup/shutdown"""
#     global orchestrator
#     # Startup
#     orchestrator = WorkflowBuilderOrchestrator(
#         api_key="your-api-key-here",
#         node_types=NODE_TYPES
#     )
#     yield
#     # Shutdown - cleanup if needed
#     orchestrator = None

# app = FastAPI(
#     title="Workflow Builder API",
#     description="AI-powered n8n workflow builder",
#     version="1.0.0",
#     lifespan=lifespan
# )

# # Add CORS middleware for Streamlit frontend
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, restrict this
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Request/Response Models
# class WorkflowRequest(BaseModel):
#     """User request to build a workflow"""
#     message: str
#     session_id: Optional[str] = None

# class WorkflowResponse(BaseModel):
#     """API response with workflow data"""
#     nodes: List[Dict[str, Any]]
#     connections: Dict[str, Any]
#     response: str
#     session_id: str

# class HealthResponse(BaseModel):
#     """Health check response"""
#     status: str
#     message: str

# # Routes
# @app.get("/health", response_model=HealthResponse)
# async def health_check():
#     """Health check endpoint"""
#     return {
#         "status": "healthy",
#         "message": "Workflow Builder API is running"
#     }

# @app.get("/node-types")
# async def get_node_types():
#     """Get available node types"""
#     return {
#         "node_types": NODE_TYPES,
#         "count": len(NODE_TYPES)
#     }

# @app.post("/workflow", response_model=WorkflowResponse)
# async def build_workflow(request: WorkflowRequest):
#     """Build a workflow based on user description"""
#     if not orchestrator:
#         raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
#     if not request.message.strip():
#         raise HTTPException(status_code=400, detail="Message cannot be empty")
    
#     try:
#         # Process message
#         result = await orchestrator.process_message(request.message)
        
#         # Extract workflow data
#         workflow = result["workflow_json"]
#         nodes = [node.to_dict() for node in workflow.nodes]
        
#         # Get assistant response
#         assistant_message = result["messages"][-1]["content"] if result["messages"] else "Workflow built successfully"
        
#         return {
#             "nodes": nodes,
#             "connections": workflow.connections,
#             "response": assistant_message,
#             "session_id": request.session_id or "default"
#         }
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error building workflow: {str(e)}")

# @app.get("/workflow/{workflow_id}")
# async def get_workflow(workflow_id: str):
#     """Get workflow details (placeholder for future implementation)"""
#     return {
#         "workflow_id": workflow_id,
#         "message": "Workflow retrieval not yet implemented"
#     }

# @app.post("/workflow/{workflow_id}/execute")
# async def execute_workflow(workflow_id: str):
#     """Execute a workflow (placeholder for future implementation)"""
#     return {
#         "workflow_id": workflow_id,
#         "status": "Execution not yet implemented"
#     }

# # WebSocket endpoint for real-time updates (optional)
# @app.websocket("/ws/workflow")
# async def websocket_endpoint(websocket: WebSocket):
#     """WebSocket endpoint for real-time workflow building"""
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_json()
#             message = data.get("message", "")
            
#             if message:
#                 result = await orchestrator.process_message(message)
#                 workflow = result["workflow_json"]
                
#                 response = {
#                     "nodes": [node.to_dict() for node in workflow.nodes],
#                     "connections": workflow.connections,
#                     "response": result["messages"][-1]["content"] if result["messages"] else ""
#                 }
                
#                 await websocket.send_json(response)
#     except Exception as e:
#         print(f"WebSocket error: {e}")
#     finally:
#         await websocket.close()

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)




# main.py - FastAPI Backend
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables
load_dotenv()

# Import after loading env
from submain import WorkflowBuilderOrchestrator

# Load node types
try:
    with open("node_types.json", "r", encoding="utf-8") as f:
        NODE_TYPES = json.load(f)
except FileNotFoundError:
    print("Warning: node_types.json not found, using empty list")
    NODE_TYPES = []

# Global orchestrator instance
orchestrator = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for app startup/shutdown"""
    global orchestrator
    
    # Startup
    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment variables")
        
        orchestrator = WorkflowBuilderOrchestrator(
            api_key=api_key,
            node_types=NODE_TYPES
        )
        print("✅ Orchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {e}")
        raise
    
    yield
    
    # Shutdown
    orchestrator = None
    print("🔄 Orchestrator shutdown complete")

app = FastAPI(
    title="Workflow Builder API",
    description="AI-powered n8n workflow builder",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class WorkflowRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class WorkflowResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    connections: Dict[str, Any]
    response: str
    session_id: str

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str

# Routes
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Workflow Builder API is running"
    }


@app.get("/node-types")
async def get_node_types():
    """Get available node types"""
    return {
        "node_types": NODE_TYPES[:20],  # Limit to first 20 for performance
        "count": len(NODE_TYPES)
    }

@app.post("/workflow", response_model=WorkflowResponse)
async def build_workflow(request: WorkflowRequest):
    """Build a workflow based on user description"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        print("Received message: ")
        # Process message
        result = await orchestrator.process_message(request.message)
        print("result testing  : ",result)
        # Extract workflow data
        workflow = result.get("workflow_json", {})
        nodes = workflow.get("nodes", [])
        print(278)
        # Convert nodes to dict if needed
        if nodes and hasattr(nodes[0], 'to_dict'):
            nodes = [node.to_dict() for node in nodes]
        print(282)
        # Get assistant response
        messages = result.get("messages", [])
        assistant_message = messages[-1].get("content", "Workflow built successfully") if messages else "Workflow built successfully"
        
        return {
            "nodes": nodes,
            "connections": workflow.get("connections", {}),
            "response": assistant_message,
            "session_id": request.session_id or "default"
        }
    
    except Exception as e:
        print(f"Error in build_workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Error building workflow: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting Workflow Builder API...")
#     print("📝 Make sure GROQ_API_KEY is set in .env file")
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)