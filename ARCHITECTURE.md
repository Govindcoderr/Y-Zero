# 🎯 Architecture & Data Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                             │
│                  (http://localhost:8501)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    HTTP GET/POST
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    STREAMLIT FRONTEND                            │
│                    (streamlit_app.py)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐  │
│  │   Sidebar Menu      │  │   Main Content Area              │  │
│  ├─────────────────────┤  ├──────────────────────────────────┤  │
│  │ • API Status        │  │  Input: Describe workflow        │  │
│  │ • API URL Config    │  │  Output: Tabs                    │  │
│  │ • Node Types        │  │    1. Workflow (Nodes)           │  │
│  │ • Example Prompts   │  │    2. Connections                │  │
│  └─────────────────────┘  │    3. Chat                       │  │
│                           │    4. JSON Export                │  │
│                           └──────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    HTTP POST /workflow
                    HTTP GET /node-types
                    HTTP GET /health
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  FASTAPI BACKEND SERVER                          │
│                    (main.py @ :8000)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ FastAPI App      │  │ CORS Middleware  │  │ Lifespan Mgmt │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
│           │                                                       │
│  ┌────────┴────────────────────────────────────────────────┐    │
│  │            REQUEST ROUTING                              │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │                                                           │    │
│  │  GET /health          → Health check                    │    │
│  │  GET /node-types      → List node definitions           │    │
│  │  POST /workflow       → Build workflow                  │    │
│  │  GET /workflow/{id}   → Get workflow details (stub)     │    │
│  │  (WS /ws/workflow     → Optional future real-time)      │    │
│  │                                                           │    │
│  └────────────────────────┬─────────────────────────────────┘   │
└─────────────────────────────┼────────────────────────────────────┘
                              │
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│                WORKFLOW ORCHESTRATOR                              │
│                    (main.py)                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │ Node Search     │  │ Builder Agent   │  │ Configurator   │  │
│  │ Engine          │  │                 │  │ Agent          │  │
│  └─────────────────┘  └─────────────────┘  └────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ LANGGRAPH STATE MACHINE                                  │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                            │   │
│  │  Supervisor → Discovery → Builder → Configurator        │   │
│  │      ↑                                      ↓             │   │
│  │      └──────────────────────────────────────┘            │   │
│  │                                                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                    │
│  ┌───────────────────────────▼──────────────────────────────┐   │
│  │ TOOLS AVAILABLE TO AGENTS                               │   │
│  ├────────────────────────────────────────────────────────┤   │
│  │ • Search Nodes          • Add Node                       │   │
│  │ • Get Node Details      • Connect Nodes                  │   │
│  │ • Update Parameters     • Validate Workflow             │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      LLM PROVIDER                                │
│                   (llm_provider.py)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Groq API (Default)                                      │   │
│  │ • High speed inference                                  │   │
│  │ • Context: 32k tokens                                   │   │
│  │ • Models: llama-3.1, mixtral, etc.                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  (Optional: Can switch to OpenAI, Anthropic, etc.)              │
│                                                                   │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
USER REQUEST (Describe Workflow)
        │
        ▼
┌──────────────────────────┐
│ Streamlit Frontend       │
│ Capture User Input       │
└──────────────┬───────────┘
               │
               │ POST /workflow
               │ {message: "..."}
               │
        ▼──────────────────
┌──────────────────────────┐
│ FastAPI Server           │
│ Parse Request            │
│ Validate Input           │
└──────────────┬───────────┘
               │
               │ Call Orchestrator
               │
        ▼──────────────────
┌──────────────────────────┐
│ WorkflowOrchestrator     │
│ Create Initial State     │
│ Add Message to History   │
└──────────────┬───────────┘
               │
               │ Invoke Graph
               │
        ▼──────────────────
┌──────────────────────────┐
│ LangGraph Execution      │
├──────────────────────────┤
│ Entry: Greeter Node      │
│ ├─ Classify user intent  │
│ ├─ Short-circuit greeting/guide/out-of-scope
│ ├─ If workflow intent: supervisor
│ └─ Else: return assistant reply
└──────────────┬───────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
 ┌────────┐ ┌────────┐ ┌─────────┐
 │Discovery│ │Builder │ │Configure│
 │ Agent   │ │ Agent  │ │ Agent   │
 └────────┘ └────────┘ └─────────┘
    │          │          │
    └──────────┼──────────┘
               │
        ▼──────────────────
┌──────────────────────────┐
│ Call LLM (Groq)          │
│ • Analyze requirements   │
│ • Generate nodes         │
│ • Define connections     │
│ • Configure parameters   │
└──────────────┬───────────┘
               │
        ▼──────────────────
┌──────────────────────────┐
│ Build Workflow State     │
│ • Add Nodes              │
│ • Create Connections     │
│ • Update Parameters      │
│ • Log Coordination       │
└──────────────┬───────────┘
               │
        ▼──────────────────
┌──────────────────────────┐
│ Responder Node           │
│ Generate Final Response  │
│ Format Results           │
└──────────────┬───────────┘
               │
        ▼──────────────────
┌──────────────────────────┐
│ Return to Frontend       │
│ ├─ Nodes array           │
│ ├─ Connections object    │
│ ├─ Assistant response    │
│ └─ Session ID            │
└──────────────┬───────────┘
               │
        ▼──────────────────
┌──────────────────────────┐
│ Streamlit Display        │
│ ├─ Show Nodes            │
│ ├─ Show Connections      │
│ ├─ Add to Chat           │
│ └─ Enable Export         │
└──────────────────────────┘
```

## Component Interaction Matrix

```
┌─────────────┬────────────┬──────────┬─────────────┐
│ Component   │ Calls      │ Called By│ Returns     │
├─────────────┼────────────┼──────────┼─────────────┤
│ Streamlit   │ API        │ Browser  │ UI/JSON     │
│ FastAPI     │ Orchestr.  │ Streamlit│ JSON        │
│ Orchestr.   │ LLM, Tools │ FastAPI  │ WorkflowObj │
│ LLM (Groq)  │ None       │ Orchestr.│ Text/JSON   │
│ Tools       │ None       │ Agents   │ Results     │
│ Agents      │ Tools, LLM │ Orchestr.│ Actions     │
└─────────────┴────────────┴──────────┴─────────────┘
```

## Request/Response Example

### Frontend Request
```json
{
  "message": "Create a workflow that checks weather API every hour"
}
```

### API Processing
```
1. Validate input
2. Create initial state
3. Run LangGraph
4. Execute agents
5. Build workflow structure
```

### Backend Response
```json
{
  "nodes": [
    {
      "id": "node_1",
      "name": "Schedule Trigger",
      "type": "workflow.scheduleTrigger",
      "parameters": {}
    }
  ],
  "connections": {},
  "response": "Workflow built successfully with 1 node",
  "session_id": "default"
}
```

### Frontend Display
- Tab 1: Shows 1 node
- Tab 2: Shows connections (empty)
- Tab 3: Adds to chat history
- Tab 4: Shows raw JSON

## Technology Stack

```
Frontend:
├── Streamlit (UI Framework)
├── Requests (HTTP Client)
└── CSS (Custom Styling)

Backend:
├── FastAPI (Web Framework)
├── Uvicorn (ASGI Server)
├── Pydantic (Data Validation)
└── Python Async/Await

Orchestration:
├── LangGraph (State Graph)
├── LangChain (LLM Tools)
└── Groq API (LLM Provider)

Deployment:
├── Docker (Containerization)
└── Docker Compose (Orchestration)
```

---

This architecture provides:
✅ Separation of concerns (Greeter / Supervisor / Discovery / Builder / Configurator / Responder are distinct jobs)
✅ Scalability (API + UI separated, LangGraph orchestrator for extending phases)
✅ Real-time capabilities (Streamlit UI with status checks, optional websocket hooks in backend)
✅ Easy deployment (FastAPI + Streamlit, .env-configurable LLM + node source)
✅ Type safety (Pydantic models in `main.py`, `Backend/types`, and typed agents/state)
✅ Modern tech stack (LangChain/Groq, LangGraph, n8n-style node graph, fuzzy search)

Also this flow covers:
- Intent gating before execution (greeter avoids wasted AI tasks)
- Tool-bound workflow mutations (`add_node`,`connect_nodes`,`validate_workflow`)
- Deterministic phase route by supervisor (prevents endless loops)
- Rich state logging via coordination log for observability
- Node resolution via `NodeSearchEngine` (fuzzy, exact and fallback)
- Componentized future growth: persistence, RAG knowledge hub, secure auth

