# AI Workflow JSON Builder Backend: Complete Technical Guide

> **Document Scope:** Backend implementation 

---

## 📋 Table of Contents

1. [Purpose & Goal](#purpose--goal)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Backend User Flow](#backend-user-flow)
5. [Architecture & Data Models](#architecture--data-models)
6. [Core Components](#core-components)
7. [Implementation Details](#implementation-details)
8. [Data Flow Diagrams](#data-flow-diagrams)
9. [State Management](#state-management)
10. [Tool System](#tool-system)
11. [Node Search & Resolution](#node-search--resolution)
12. [Workflow Generation Pipeline](#workflow-generation-pipeline)
13. [Error Handling & Resilience](#error-handling--resilience)

---

## 1. Purpose & Goal

**Purpose:** Convert plain English workflow descriptions into executable Y-Zero workflow JSON using AI agents.

**Goals:**
- **Deterministic Building:** Use tool calls to build accurate workflow graphs
- **Smart Node Search:** Fast fuzzy search of node catalog via Elasticsearch
- **Multi-Agent Pipeline:** 5-phase agent system for robust workflow creation
- **Resilient Design:** Works with or without Elasticsearch

---

## 2. Problem Statement

**Problem:** Manual workflow building is slow and error-prone. Users must:
- Drag/drop nodes manually
- Learn complex node APIs
- Debug connection issues
- Set parameters through trial-and-error

**Need:** Describe workflows in plain English, get working JSON automatically.

**Example:** "Fetch API data every 2 hours, extract emails, send to Slack" → Complete workflow JSON

---

## 3. Solution Overview

**Solution:** Multi-agent AI pipeline converts natural language to workflow JSON.

**Key Innovation:** Tool-driven construction using LLM agents that:
1. Search node catalog
2. Add nodes with UUIDs
3. Connect nodes properly
4. Set parameters intelligently
5. Validate final structure

**Result:** Valid workflow JSON from plain English descriptions.

```
┌─────────────────────────────────────────────────────────────────┐
│  User Request (natural language)                                │
│  "Fetch HTTP data, extract emails, send to Slack at 9 AM"      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    ┌──────▼────────┐
                    │ FastAPI/Async │
                    │   Endpoint    │
                    └──────┬────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │   LangGraph Orchestration Pipeline  │
        │  ┌▼──────┐  ┌▼──────────┐          │
        │  │Greeter├─>│Supervisor │          │
        │  └───────┘  └┬────┬─────┘          │
        │             │    │                 │
        │      ┌──────▼┐   │      ┌─────────┐│
        │      │Discovery  │      │Responder││
        │      └┬─────┬─┐  │      └────┬────┘│
        │       │     │ │  │           │     │
        │    ┌──▼─┐   │ │ ┌▼──────────┐│     │
        │    │Buil│   │ │ │Configurator││     │
        │    │der │   │ │ └────────────┘│     │
        │    └────┘   └─┴──────────────┘│     │
        └────────────────────────────────┘     │
                           │                    │
        ┌──────────────────▼──────────────────┐
        │  Workflow JSON Output               │
        │  {                                  │
        │    "nodes": [                       │
        │      {                              │
        │        "id": "node_1",              │
        │        "type": "HTTP REQUEST",      │
        │        "parameters": {...}         │
        │      },                             │
        │      {                              │
        │        "id": "node_2",              │
        │        "type": "SLACK",             │
        │        "parameters": {...}         │
        │      }                              │
        │    ],                               │
        │    "edges": [                       │
        │      {                              │
        │        "source": "node_1",          │
        │        "target": "node_2"           │
        │      }                              │
        │    ]                                │
        │  }                                  │
        └─────────────────────────────────────┘
```

### Key Innovation
**Tool-Driven Construction** — The LLM agent doesn't generate raw JSON; instead, it:
1. **Searches** for the right node types
2. **Adds** nodes one by one (getting back UUIDs)
3. **Connects** nodes via UUIDs + parameter mappings
4. **Updates** parameters with intelligent defaults
5. **Validates** the final workflow structure

This ensures **structural correctness** before serialization.

---

## 4. Backend User Flow

**Flow:** User request → FastAPI → LangGraph agents → Workflow JSON response.

**Key Phases:**
1. **API Ingestion:** Validate request, initialize workflow state
2. **Greeter:** Detect if greeting/chat or workflow request
3. **Supervisor:** Route to discovery/builder/configurator/responder
4. **Discovery:** Analyze intent and categorize automation type
5. **Builder:** Use tools to construct workflow graph
6. **Configurator:** Set node parameters intelligently
7. **Responder:** Generate final response with workflow JSON

---

## 5. Architecture & Data Models

**Core Classes:**
- **SimpleWorkflow:** Holds name, nodes, connections
- **WorkflowNode:** Node with id, name, type, parameters, position
- **WorkflowState:** LangGraph state with messages, workflow, categorization

**Node Registry:** JSON catalog of available automation nodes (HTTP, Slack, etc.) with properties and actions.

---

## 6. Core Components

### 6.1 FastAPI Backend (main.py)

**Responsibilities:**
- HTTP request routing
- Input validation (WorkflowRequest)
- Orchestrator lifecycle management
- Response serialization (WorkflowResponse)
- Admin endpoints (reindex, ES status)

**Key Endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/workflow` | POST | Build workflow from message |
| `/admin/reindex` | POST | Re-sync nodes to Elasticsearch |
| `/admin/es-status` | GET | Check ES connectivity |

**Lifespan Hooks:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    # 1. Load nodes from Elasticsearch (or fallback)
    # 2. Initialize Orchestrator
    # 3. Reindex nodes if ES available
    
    yield  # Server runs
    
    # Shutdown:
    # Clean up resources
```

### 6.2 LangGraph Orchestrator (submain.py)

**Responsibilities:**
- Graph compilation (6 agent nodes + routing)
- Per-request workflow instance creation
- Tool binding to workflow objects
- State flow management
- Async invocation

**Graph Structure:**
```
Entry → [Greeter] → {greeter_proceed?}
                         ├─> YES → [Supervisor] ← ┐
                         │            │             │
                         ├─────────────▼─────────── [Discovery]
                         │                          [Builder]
                         │                          [Configurator]
                         │            │             │
                         │            └─────────────┘
                         │
                         └─> NO → END
                        
[Supervisor] → [Responder] → END
```

### 6.3 Multi-Agent System

#### **Agent 1: Greeter** (agents/greeter.py)
- **Input:** User message
- **Logic:** Classify intent as greeting/guide/workflow
- **Output:** {"intent": str, "should_proceed": bool, "response": str}
- **Short-circuit:** If not a workflow request, ends pipeline

#### **Agent 2: Supervisor** (agents/supervisor.py)
- **Input:** WorkflowState
- **Logic:** Deterministic router (no LLM call) based on state fields
- **Output:** {"next_agent": "discovery"|"builder"|"configurator"|"responder"}
- **Route Decision:**
  ```
  if not categorization:        return "discovery"
  elif not workflow.nodes:      return "builder"
  elif incomplete_params:       return "configurator"
  else:                         return "responder"
  ```

#### **Agent 3: Discovery** (agents/discovery.py)
- **Input:** User message
- **Logic:** Analyze intent, extract techniques, classify domain
- **Output:** {"categorization": DomainCategorization, "best_practices": [...]}
- **Stores:** In state.categorization object

#### **Agent 4: Builder** (agents/builder.py)
- **Input:** User message + available nodes
- **Logic:** Tool-calling loop to construct workflow
- **Tools Available:**
  - `search_nodes(query)` → Find node matches
  - `add_node(type, name, params)` → Add node, return UUID
  - `connect_nodes(source_id, target_id, type)` → Create edge
  - `validate_workflow()` → Check structure
- **Output:** {"nodes_added": int, "summary": str}
- **Mutation:** Directly updates workflow_json.nodes + .connections

#### **Agent 5: Configurator** (agents/configurator.py)
- **Input:** Incomplete workflow (nodes present but missing params)
- **Logic:** Iterate nodes, fill missing parameters intelligently
- **Tools Available:**
  - `update_parameters(node_id, params)` → Set node config
  - `validate_workflow()` → Verify after each change
- **Output:** {"nodes_configured": int, "summary": str}
- **Mutation:** Updates workflow_json.nodes[*].parameters

#### **Agent 6: Responder** (agents/responder.py)
- **Input:** Complete workflow
- **Logic:** Generate human-friendly summary
- **Output:** {"response": str}
- **Store:** Appends to messages list

---

## 7. Implementation Details

### 7.1 Tool System Architecture

All tools follow this pattern:

```python
def create_X_tool(workflow: SimpleWorkflow, ...) -> Tool:
    """
    Factory function that binds a tool to a specific workflow instance.
    Returns a LangChain Tool object with bound context.
    """
    
    async def tool_function(params: Dict) -> str:
        # Mutate workflow object
        # Return structured result for LLM feedback
        pass
    
    return Tool(
        name="tool_name",
        description="...",
        func=tool_function,
        args_schema=ToolInputSchema
    )
```

**Example: add_node Tool** (backend/tools/add_node.py)
```python
async def add_node_impl(node_type: str, name: str, params: dict):
    """
    1. Resolve node_type via search_engine.resolve_node_type()
    2. Generate UUID for node
    3. Create WorkflowNode instance
    4. Append to workflow.nodes
    5. Return {node_id: UUID, message: "Added..."}
    """
    resolved_type = search_engine.resolve_node_type(node_type)
    node_id = str(uuid.uuid4())
    
    node = WorkflowNode(
        id=node_id,
        name=name,
        type=resolved_type,
        parameters=params,
        position=(0, 0)  # positioning handled later
    )
    
    workflow.nodes.append(node)
    return {"node_id": node_id, "message": f"Added {name}"}
```

**Example: connect_nodes Tool** (backend/tools/connect_nodes.py)
```python
async def connect_by_name_impl(source_name: str, target_name: str, type: str):
    """
    1. Validate source_name and target_name exist in workflow.nodes
    2. Find node IDs by name
    3. Update workflow.connections[source_name][type]
    4. Return validation result
    """
    source = find_node_by_name(workflow, source_name)
    target = find_node_by_name(workflow, target_name)
    
    if not source or not target:
        return {"error": "Node not found"}
    
    # Create connection
    conn = WorkflowConnection(node=target.name, type=type)
    
    if source_name not in workflow.connections:
        workflow.connections[source_name] = {}
    if type not in workflow.connections[source_name]:
        workflow.connections[source_name][type] = []
    
    workflow.connections[source_name][type].append([conn])
    
    return {"status": "ok", "connection": f"{source_name} → {target_name}"}
```

### 7.2 Tool Binding Per Request

**Why per-request?**
- Each user request gets a fresh workflow object
- Tools must mutate the current workflow, not a global one
- Previous conversations must not affect new workflows

**Implementation:**
```python
async def _builder_node(state: WorkflowState) -> Dict:
    workflow = state["workflow_json"]
    
    # Create fresh tools bound to THIS workflow
    builder_tools, _ = self._create_request_tools(workflow)
    builder = BuilderAgent(self.llm, builder_tools, self.search_engine)
    
    result = await builder.build_workflow(state)
    return result
```

### 7.3 LLM Integration

**LLM Providers** (llm_provider.py)
```python
def get_llm(api_key: str):
    """Returns tool-calling LLM (Groq w/ function calling)"""
    return ChatGroq(
        model="mixtral-8x7b-32768",
        temperature=0,  # Deterministic
        groq_api_key=api_key,
        streaming=False
    )

def get_llm_no_tools():
    """Returns plain LLM for analysis (no tool binding)"""
    return ChatGroq(
        model="mixtral-8x7b-32768",
        temperature=0.3,  # Slight variation for creativity
        groq_api_key=api_key
    )
```

**Why Two LLMs?**
1. **With tools** (builder/configurator): Must support function calling
2. **Plain** (greeter/supervisor/discovery): Pure text analysis + classification

---

## 8. Data Flow Diagrams

### 8.1 Request to Response Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. HTTP POST /workflow                                           │
│    { "message": "Fetch HTTP data and send to Slack", ... }      │
└──────────────────┬───────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────┐
│ 2. FastAPI Endpoint (main.py)                                    │
│    - Validate request                                            │
│    - Check orchestrator readiness                                │
│    - Call orchestrator.process_message()                         │
└──────────────────┬───────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────┐
│ 3. Create Initial State (WorkflowState)                          │
│    - Empty workflow object (SimpleWorkflow)                      │
│    - Messages: [{"role": "user", "content": "..."}]             │
│    - coordination_log: []                                        │
│    - greeter_proceed: False (default)                            │
└──────────────────┬───────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────┐
│ 4. LangGraph Invocation (submain.py)                             │
│    graph.ainvoke(state) → Runs through all nodes                 │
└──────────────────┬───────────────────────────────────────────────┘
                   │
        ┌──────────┴───────────┐
        │                      │
┌───────▼────────┐    ┌────────▼──────────┐
│ Greeter Agent  │    │ Check: greeting?  │
│                │    │ out-of-scope?     │
└────┬───────────┘    └────────┬──────────┘
     │                         │
     ├─────────[ YES ]─────────┤
     │                         ▼
     │                  Set greeter_proceed=False
     │                  Append response message
     │                  END (return state)
     │
     └─────────[ NO ]──────────┐
                               │
                      ┌────────▼──────────┐
                      │ Set greeter_proceed=True
                      │ Continue to Supervisor
                      └────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │ Supervisor: Route Based    │
                │ on State Fields            │
                └────┬──────────┬──────────┬──┘
                     │          │          │
          ┌──────────▼┐ ┌──────▼─┐ ┌────▼──────┐
          │Discovery  │ │Builder │ │Configurator
          │           │ │        │ │            │
          └─────┬─────┘ └────┬───┘ └────┬───────┘
                │            │         │
                └────────────┬┴────────┬┘
                             │        │
                      ┌──────▼────────▼───┐
                      │ Loop Back to      │
                      │ Supervisor Until  │
                      │ All Done          │
                      └────────┬──────────┘
                               │
                        ┌──────▼───────┐
                        │ Responder:   │
                        │ Final Output │
                        └────────┬─────┘
                                 │
                          ┌──────▼──────┐
                          │ Extract     │
                          │ from state: │
                          │ - nodes     │
                          │ - edges     │
                          │ - messages  │
                          └────────┬────┘
                                   │
                            ┌──────▼─────────┐
                            │ Convert to     │
                            │ WorkflowResponse
                            │                │
                            │ {              │
                            │  "id": 1,      │
                            │  "nodes": [...],
                            │  "edges": [...],
                            │  "response": "✅",
                            │  ...           │
                            │ }              │
                            └────────┬───────┘
                                     │
                              ┌──────▼────────┐
                              │ HTTP 200 OK  │
                              │ (JSON)       │
                              └──────────────┘
```

### 8.2 Node Search Flow

```
┌────────────────────────────────────────┐
│ LLM Agent Needs Node                   │
│ Calls: search_nodes("http")           │
└────────────────┬───────────────────────┘
                 │
         ┌───────▼────────┐
         │ NodeSearchEngine
         │.search_by_name()
         └───────┬────────┘
                 │
        ┌────────▼─────────┐
        │ Try Elasticsearch
        │ es.multi_match   │
        │ query with       │
        │ fuzziness        │
        └────┬─────────┬───┘
             │         │
         [SUCCESS]  [FAIL]
             │         │
       ┌─────▼───┐   ┌─▼──────────────┐
       │ Return  │   │ Fallback:      │
       │ Results │   │ In-memory      │
       │         │   │ sublimeSearch()
       └─────┬───┘   └─┬──────────────┘
             │        │
             └────┬───┘
                  │
         ┌────────▼─────────┐
         │ Format Results   │
         │ for LLM          │
         │ (XML or JSON)    │
         └────────┬─────────┘
                  │
         ┌────────▼──────────┐
         │ Return to LLM     │
         │ [{                │
         │   "name": "...",  │
         │   "score": 0.95,  │
         │   "type": "action"│
         │ }, ...]          │
         └──────────────────┘
```

---

## 9. State Management

### 9.1 LangGraph State Reducers

The WorkflowState uses custom reducers for specific fields:

```python
# messages field: uses add_messages reducer (LangChain built-in)
# - Merges new messages intelligently
# - Dedupes by message ID
# - Preserves order

# coordination_log field: uses custom merge reducer
# - Appends phases in order
# - No deduping (each phase is unique)

# workflow_json field: direct replacement
# - Always replace with new workflow object
# - No merging needed (each phase has full workflow)

# categorization field: direct replacement
# - Set once by Discovery agent
# - Used by Builder for context

# best_practices field: direct replacement
# - Set once by Discovery agent
# - Reference for Configurator
```

### 9.2 State Immutability Pattern

LangGraph expects **immutable state updates**. Each node returns a dict:

```python
async def _builder_node(state: WorkflowState) -> Dict[str, Any]:
    workflow = state["workflow_json"]  # Read immutable state
    
    # Work with the object inside state
    builder_tools, _ = self._create_request_tools(workflow)
    builder = BuilderAgent(self.llm, builder_tools)
    
    result = await builder.build_workflow(state)
    
    # Return NEW dict (LangGraph merges into state)
    return {
        "coordination_log": [log_entry],
        # workflow_json already mutated via tools
        # (tools modified the object directly)
    }
```

### 9.3 Per-Request Tool Binding

**Challenge:** Tools must mutate the workflow object, but we can't use global state.

**Solution:** Create tools for each request:

```python
class WorkflowBuilderOrchestrator:
    def _create_request_tools(self, workflow: SimpleWorkflow):
        """Called at start of Builder phase"""
        
        # Each tool receives the workflow instance
        builder_tools = [
            create_search_nodes_tool(self.search_engine),           # Read-only
            create_add_node_tool(workflow, self.search_engine),     # Mutates workflow
            create_connect_nodes_tool(workflow),                    # Mutates workflow
            create_validate_workflow_tool(workflow),                # Read-only
        ]
        
        return builder_tools
```

**Benefits:**
- ✅ Each request gets isolated tools
- ✅ Tools mutate the correct workflow object
- ✅ No cross-request contamination
- ✅ Easy to debug (trace which tool modified what)

---

## 10. Tool System

### 10.1 Tool Inventory

| Tool | Phase | Type | Purpose |
|------|-------|------|---------|
| `search_nodes` | Builder | Read | Find node candidates by query |
| `add_node` | Builder | Write | Add node to workflow + return UUID |
| `connect_nodes_by_name` | Builder | Write | Create edge using node names |
| `connect_nodes_by_id` | Builder | Write | Create edge using UUIDs |
| `get_node_details` | Builder | Read | Inspect full node definition |
| `validate_workflow` | Builder/Config | Read | Check workflow structure validity |
| `update_parameters` | Configurator | Write | Set node parameter values |
| `resolve_node_type` | Builder | Read | Fuzzy-match user input to exact node type |

### 10.2 Tool Signatures

#### search_nodes(query: str) → List[NodeSearchResult]
```python
# Input: "http request", "slack", "schedule"
# Output: [
#   {"name": "HTTP REQUEST", "description": "...", "nodeType": "action", "score": 0.99},
#   {"name": "HTTP RESPONSE", "description": "...", "nodeType": "action", "score": 0.87},
# ]
```

#### add_node(node_type: str, name: str, parameters: dict) → dict
```python
# Input: ("HTTP REQUEST", "Fetch weather API", {"url": "https://...", ...})
# Output: {"node_id": "uuid-123-abc", "message": "Added node", "status": "ok"}
```

#### connect_nodes(source_name: str, target_name: str, connection_type: str) → dict
```python
# Input: ("HTTP node", "Slack node", "output")
# Output: {"status": "ok", "message": "Connected HTTP node → Slack node"}
```

#### update_parameters(node_id: str, parameters: dict) → dict
```python
# Input: ("uuid-123", {"url": "https://...", "timeout": 30})
# Output: {"status": "ok", "updated_fields": ["url", "timeout"]}
```

---

## 11. Node Search & Resolution

### 11.1 Search Engine Architecture

Located in: **backend/engines/node_search_engine.py**

```python
class NodeSearchEngine:
    def __init__(self, node_types: List[dict]):
        self.node_types = node_types
        self._build_registry()
        self._try_init_es()  # Try Elasticsearch
        if not _es_available:
            self._init_fallback_search()  # Fall back to in-memory
    
    def search_by_name(self, query: str, limit: int = 5):
        """Multi-source search"""
        if self._es_available:
            return self._es_search(query, limit)
        else:
            return self._fallback_search(query, limit)
    
    def resolve_node_type(self, user_input: str) -> str:
        """Fuzzy-match user input to exact node type"""
        results = self.search_by_name(user_input, limit=1)
        if results:
            return results[0]["name"]  # e.g., "HTTP REQUEST"
        return "HTTP REQUEST"  # Safe default
```

### 11.2 Elasticsearch Integration

**Index Schema:**
```
Index: yzero_nodes

Document:
{
  "_id": "http-request-v1",
  "name": "HTTP REQUEST",
  "displayName": "HTTP Request",
  "nodeType": "action",
  "description": "Make HTTP requests to URLs",
  "_raw": "base64(full_node_definition)"
  // Indexed fields for fuzzy search
}
```

**Search Query:**
```json
{
  "multi_match": {
    "query": "http",
    "fields": [
      "displayName^1.5",
      "name^1.3",
      "description^0.7"
    ],
    "fuzziness": "AUTO",
    "prefix_length": 0
  }
}
```

### 11.3 Fallback Search (In-Memory)

When Elasticsearch unavailable:
```python
def sublime_search(query: str, nodes: list) -> List[tuple]:
    """
    Python port of @Y-Zero/utils sublimeSearch
    
    Algorithm:
    1. For each node, score against query
    2. Score each field (displayName, name, codex.alias, description)
    3. Weight by importance (displayName > name > description)
    4. Fuzzy match if no exact match
    5. Return top N by score
    """
    scores = []
    for node in nodes:
        score = 0
        score += field_score("http", node["displayName"], weight=1.5)
        score += field_score("http", node["name"], weight=1.3)
        score += field_score("http", node["description"], weight=0.7)
        
        if score > 0:
            scores.append((score, node))
    
    return sorted(scores, key=lambda x: x[0], reverse=True)
```

**Scoring Function:**
```
Exact match (field == query)           → score * 1.00
Prefix match (field starts with)       → score * 0.90
Contains match (query in field)        → score * 0.80
Partial word match (n/k words match)   → score * (n/k) * 0.70
Fuzzy match (SequenceMatcher > 0.45)   → score * fuzzy_ratio * 0.55
```

---

## 12. Workflow Generation Pipeline

### 12.1 Step-by-Step Workflow Building

**Example Request:** 
```
"Fetch JSON from https://api.example.com/data every 2 hours, 
extract the 'email' field, and send it to Slack"
```

**Step 1: Greeter Analysis**
```
Intent Detection:
  - Contains verbs: "fetch", "send"
  - No greeting words: "hello", "thanks"
  - Action requested: YES
  
Decision: greeter_proceed = True
```

**Step 2: Supervisor Route**
```
State check:
  - categorization: null → NEED DISCOVERY
  - workflow.nodes: [] → NEED BUILDER
  
Next agent: discovery
```

**Step 3: Discovery Analysis**
```
Input: User message

LLM Analysis:
  - Techniques: [POLLING_SCHEDULE, DATA_TRANSFORMATION, MESSAGE_DELIVERY]
  - Domain: API_INTEGRATION
  - Confidence: 0.92
  - Best practices:
    * "Use HTTP node with retry logic"
    * "Set timeout to 30s for API calls"
    * "Validate JSON response before processing"
    * "Use error handler for Slack failures"

Output: DomainCategorization
```

**Step 4: Supervisor Route Again**
```
State check:
  - categorization: ✓ (set by discovery)
  - workflow.nodes: [] (still empty) → NEED BUILDER
  
Next agent: builder
```

**Step 5: Builder Agentic Loop**

**Iteration 1: Choose Trigger**
```
LLM Thinking:
  "User wants 'every 2 hours' → need a schedule trigger"
  
LLM Action:
  search_nodes("schedule")
  
Result:
  [
    {name: "SCHEDULE", score: 0.98},
    {name: "CRON", score: 0.85},
    {name: "TRIGGER", score: 0.72}
  ]

LLM Observation:
  "SCHEDULE is the best match"
  
LLM Action:
  add_node("SCHEDULE", "Schedule trigger every 2 hours", {
    "interval": 2,
    "unit": "hours"
  })
  
Tool Result:
  {
    "node_id": "node_uuid_1",
    "message": "Added SCHEDULE node",
    "status": "ok"
  }

State Update:
  workflow.nodes = [
    WorkflowNode(
      id="node_uuid_1",
      name="Schedule trigger every 2 hours",
      type="SCHEDULE",
      parameters={"interval": 2, "unit": "hours"},
      position=(0, 0)
    )
  ]
```

**Iteration 2: Add HTTP Fetch**
```
LLM Thinking:
  "After schedule triggers, fetch data from URL"
  
LLM Action:
  search_nodes("http fetch")
  
Result:
  [
    {name: "HTTP REQUEST", score: 0.99},
    {name: "GET", score: 0.81},
    {name: "FETCH", score: 0.78}
  ]

LLM Action:
  add_node("HTTP REQUEST", "Fetch API data", {
    "url": "https://api.example.com/data",
    "method": "GET",
    "timeout": 30
  })
  
Tool Result:
  {"node_id": "node_uuid_2", ...}

LLM Action:
  connect_nodes("Schedule trigger every 2 hours", "Fetch API data", "output")
  
State Update:
  workflow.nodes.append(HTTP REQUEST node)
  workflow.connections = {
    "Schedule trigger every 2 hours": {
      "output": [[WorkflowConnection(node="Fetch API data", type="output")]]
    }
  }
```

**Iteration 3: Add Data Transform**
```
LLM Thinking:
  "Response has multiple fields, extract just 'email'"
  
LLM Action:
  search_nodes("code transform javascript")
  
Result:
  [
    {name: "CODE", score: 0.96},
    {name: "JAVASCRIPT", score: 0.89},
    {name: "TRANSFORM", score: 0.81}
  ]

LLM Action:
  add_node("CODE", "Extract email field", {
    "language": "javascript",
    "code": "return $json.email;"
  })
  
Tool Result:
  {"node_id": "node_uuid_3", ...}

LLM Action:
  connect_nodes("Fetch API data", "Extract email field", "output")
```

**Iteration 4: Add Slack**
```
LLM Action:
  search_nodes("slack send message")
  
Result:
  [{name: "SLACK", score: 0.99}, ...]

LLM Action:
  add_node("SLACK", "Send to Slack", {
    "channel": "#notifications",
    "text": "Email: {{$json.email}}"
  })
  
Tool Result:
  {"node_id": "node_uuid_4", ...}

LLM Action:
  connect_nodes("Extract email field", "Send to Slack", "output")
```

**Iteration 5: Validate**
```
LLM Action:
  validate_workflow()
  
Tool Result:
  {
    "valid": true,
    "nodes": 4,
    "edges": 3,
    "message": "Workflow is valid"
  }

LLM Observation:
  "Validation passed! Workflow is complete."
  
Decision: Stop building
```

**Step 6: Supervisor Route Again**
```
State check:
  - workflow.nodes: 4 ✓
  - categorization: ✓
  - nodes_configured: 3/4 (Slack needs auth token)
  
Next agent: configurator
```

**Step 7: Configurator Loop**

**Iteration 1: Configure SCHEDULE**
```
Configurator LLM:
  "SCHEDULE node – check required params"
  
LLM Action:
  get_node_details("SCHEDULE")
  
Result: Required fields: [interval, unit]
  
LLM Observation:
  "Both already set in builder phase ✓"
  
Skip this node.
```

**Iteration 2: Configure HTTP REQUEST**
```
LLM Action:
  update_parameters("node_uuid_2", {
    "timeout": 30,
    "retry": 3,
    "retryWait": 5000
  })
  
Tool Result:
  {"status": "ok", "updated_fields": ["timeout", "retry"]}
```

**Iteration 3: Configure CODE**
```
LLM Action:
  update_parameters("node_uuid_3", {
    "language": "javascript",
    "code": "return {email: $json.data[0].email};"  // More robust
  })
```

**Iteration 4: Configure SLACK**
```
LLM Action:
  update_parameters("node_uuid_4", {
    "authentication": "oAuth2",  // User must provide token
    "channel": "#notifications",
    "text": "New email: {{$json.email}}",
    "botName": "AI Workflow JSON Builder"
  })
  
Tool Result:
  {"status": "ok", "notes": "Authentication token required at runtime"}
```

**Step 8: Responder Summary**
```
Response Generated:
  "✅ Workflow 'API to Slack' built successfully!
  
  📊 Summary:
    - 4 nodes added
    - 3 connections created
  
  🔗 Structure:
    • SCHEDULE (trigger)
      → HTTP REQUEST (fetch API)
      → CODE (extract email)
      → SLACK (send message)
  
  ⚙️ Next Steps:
    - Configure SLACK authentication token
    - Test workflow execution
    - Schedule deployment"
```

**Step 9: API Response**
```json
{
  "id": 1,
  "name": "API to Slack",
  "nodes": [
    {
      "id": "node_uuid_1",
      "type": "SCHEDULE",
      "data": {
        "label": "Schedule trigger every 2 hours",
        "parameters": {"interval": 2, "unit": "hours"}
      },
      "position": {"x": 0, "y": 0}
    },
    // ... more nodes
  ],
  "edges": [
    {
      "id": "edge_1",
      "source": "node_uuid_1",
      "target": "node_uuid_2"
    },
    // ... more edges
  ],
  "response": "✅ Workflow 'API to Slack' built successfully!...",
  "session_id": "user-session-123"
}
```

---

## 13. Error Handling & Resilience

### 13.1 Error Categories

| Category | Handler | Example |
|----------|---------|---------|
| **Input Validation** | FastAPI Pydantic | Empty message, invalid schema |
| **Elasticsearch Down** | Fallback search | ES unreachable → use in-memory |
| **Node Not Found** | Fuzzy resolution | User says "telegram" → resolve to "TELEGRAM" |
| **Invalid Connection** | Validation tool | Connect non-existent nodes → error + retry |
| **Missing Parameters** | Configurator loop | Required field blank → LLM fills intelligently |
| **LLM Tool Call Error** | Tool result handling | JSON parse error in tool args → sanitize |
| **Greeter Short-Circuit** | Early END | Non-workflow query → respond + exit |

### 13.2 Graceful Degradation

```python
class NodeSearchEngine:
    def search_by_name(self, query: str) -> List[dict]:
        """Multi-fallback search strategy"""
        
        try:
            # Tier 1: Elasticsearch (fast + scalable)
            if self._es_available:
                return self._es_search(query)
        except Exception as e:
            print(f"⚠️  ES search failed: {e}")
            self._es_available = False  # Mark for next time
        
        try:
            # Tier 2: In-memory fallback (always works)
            return self._fallback_search(query)
        except Exception as e:
            print(f"❌ Fallback search failed: {e}")
            # Tier 3: Return safe default
            return [{"name": "HTTP REQUEST", "score": 0.5}]
```

### 13.3 Tool Error Handling

```python
# Builder Agent
async def build_workflow(state: WorkflowState) -> dict:
    user_input = "..."
    max_iterations = 5
    
    for iteration in range(max_iterations):
        try:
            # LLM + tools loop
            response = await self.llm_with_tools.ainvoke([...])
            
            # If tools were called, execute them
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    try:
                        result = await self._execute_tool(tool_call)
                        # Add result as ToolMessage
                    except Exception as e:
                        print(f"⚠️  Tool failed: {e}")
                        # Tool failures are non-fatal
                        # LLM can retry or use different approach
        
        except Exception as e:
            print(f"❌ Build iteration {iteration} failed: {e}")
            if iteration == max_iterations - 1:
                raise  # Final retry failed
    
    return {"status": "ok", "nodes_added": len(workflow.nodes)}
```

---

## 14. Future Enhancements

### Planned Features

| Feature | Impact | Timeline |
|---------|--------|----------|
| **Multi-Turn Conversations** | Users refine workflows over multiple messages | Q2 2026 |
| **Workflow Versioning** | Track changes, rollback to prior versions | Q2 2026 |
| **Parameter Validation Rules** | Prevent invalid configurations before execution | Q3 2026 |
| **Performance Profiling** | Identify slow/costly nodes in workflow | Q3 2026 |
| **Custom Node Types** | Allow users to register custom Y-Zero nodes | Q4 2026 |
| **Workflow Templates** | Pre-built examples + variations | Q2 2026 |
| **Audit Logging** | Full trace of who built what, when | Q1 2026 |
| **Webhook Support** | Workflows triggered by HTTP events | Q3 2026 |

---

## 15. Troubleshooting Guide

### Common Issues

**Issue: "Orchestrator not initialized"**
```
Cause: GROQ_API_KEY not set or invalid
Fix:
  1. Check .env file has GROQ_API_KEY=your_key
  2. Verify key is valid at api.groq.com
  3. Check for typos or trailing whitespace
  4. Restart backend: python main.py
```

**Issue: "Elasticsearch connection refused"**
```
Cause: ES not running or URL wrong
Fix:
  1. Confirm ES running: curl http://localhost:9200
  2. Check ES_ELASTICSEARCH_URL in .env
  3. System falls back to in-memory search (works but slower)
  4. Optional: docker-compose up -d elasticsearch (start local ES)
```

**Issue: "Node not found" errors"**
```
Cause: Node not in registry or misspelled
Fix:
  1. Check node exists: GET /admin/es-status
  2. Call POST /admin/reindex to sync latest nodes
  3. Verify node JSON is valid (base64 in ES)
  4. Check ES_NODE_INDEX name matches config
```

**Issue: "Workflow validation failed"**
```
Cause: Invalid connections or structure
Fix:
  1. Check nodes exist (search_nodes tool)
  2. Verify target node is reachable (type compatible)
  3. Check parameters are not null/invalid
  4. Try validate_workflow() tool directly
  5. Check logs for detailed error message
```

---

## 16. API Reference (Backend)

### POST /workflow
```
Request:
  {
    "message": "Fetch JSON and send to Slack",
    "session_id": "user-123" (optional)
  }

Response (200):
  {
    "id": 1,
    "name": "Workflow name",
    "nodes": [NodeOut, ...],
    "edges": [EdgeOut, ...],
    "viewport": {"x": 0, "y": 0, "zoom": 1},
    "publish": 0,
    "response": "✅ Workflow built...",
    "session_id": "user-123"
  }

Response (400): Message empty
Response (503): Orchestrator not initialized
Response (500): Build failed (see error detail)
```

### GET /health
```
Response (200):
  {
    "status": "healthy",
    "message": "Workflow Builder API is running"
  }
```

### POST /admin/reindex
```
Response (200):
  {
    "status": "ok",
    "nodes_indexed": 500,
    "es_available": true
  }

Trigger: After adding new nodes to ES
Effect:  Re-syncs Elasticsearch index from node registry
```

### GET /admin/es-status
```
Response (200 + ES available):
  {
    "es_available": true,
    "backend": "elasticsearch",
    "es_doc_count": 500,
    "total_nodes_in_memory": 500
  }

Response (200 + ES down):
  {
    "es_available": false,
    "backend": "in-memory fallback",
    "total_nodes": 500
  }
```

---

## 17. Appendix: Data Models (Full Definitions)

See [backend/types/](backend/types/) for complete implementation:
- [workflow.py](backend/types/workflow.py) — SimpleWorkflow, WorkflowNode, WorkflowConnection
- [categorization.py](backend/types/categorization.py) — DomainCategorization, AutomationTechnique
- [nodes.py](backend/types/nodes.py) — NodeSearchResult, NodeDetails
- [coordination.py](backend/types/coordination.py) — CoordinationLogEntry

---

## 18. Document Metadata

- **Document Version:** 2.2
- **Last Updated:** March 27, 2026
- **Maintained By:** AI Workflow JSON Builder Backend Team
- **Scope:** Backend implementation only (no frontend/Streamlit)
- **Audience:** Backend developers, architects, DevOps

---

**End of Backend Technical Guide**
