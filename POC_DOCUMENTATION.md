# Y-Zero: Simple POC Code Flow

**Version:** 2.0 POC  
**Purpose:** AI Workflow Builder - Convert natural language to n8n workflows  
**Stack:** FastAPI + LangGraph + Groq LLM

---

## Quick Overview

```
User: "Build a workflow that gets data from API and stores in database"
    ↓
FastAPI endpoint receives message
    ↓
Orchestrator runs 5-step AI agent pipeline
    ↓
Returns: Workflow with HTTP node + Database node + connection
```

---

## The 5-Step Flow

### 1️⃣ **Supervisor** → Decides what to do next
- Looks at current state
- Decides: "discovery" OR "builder" OR "configurator" OR "responder"
- **Logic:** If empty workflow → go to builder, if needs config → go to configurator, else → done

### 2️⃣ **Discovery** → Understands user intent
- LLM reads: "get data from API and store in database"
- Extracts: "This is an API extraction + database write workflow"
- Saves: Categorization + best practices
- **Returns to supervisor** → Supervisor decides next step

### 3️⃣ **Builder** → Constructs the workflow
- Gets tools: search_nodes, add_node, connect_nodes, validate
- LLM decides: "Need HTTP node for API, need Postgres node for DB"
- **Tool calls:**
  - `search_nodes("API")` → finds HTTP node
  - `add_node("http", "Get Data", {...})`  → adds node to workflow  
  - `search_nodes("database")` → finds Postgres node
  - `add_node("postgres", "Save to DB", {...})` → adds node
  - `connect_nodes("Get Data", "Save to DB")` → creates connection
  - `validate_workflow()` → checks it's valid
- **Mutates:** workflow object gets 2 nodes + 1 connection
- **Returns to supervisor** → Supervisor checks if done

### 4️⃣ **Configurator** → Tunes parameters (if needed)
- Gets tools: update_parameters, validate
- LLM refines: "Set API URL, database table name"
- **Tool calls:** Updates node parameters
- **Returns to supervisor** → Supervisor moves to finalization

### 5️⃣ **Responder** → Formats output
- Serializes workflow to JSON
- Generates response: "✅ Built 2-node workflow"
- **Returns:** Final state
- **Graph ends**

---

## What Is The "State"?

```python
state = {
    "messages": [
        {"role": "user", "content": "Build workflow..."},
        {"role": "assistant", "content": "✅ Built workflow..."}
    ],
    "workflow_json": {
        "name": "Auto-generated",
        "nodes": [
            {"type": "http", "name": "Get Data", "params": {...}},
            {"type": "postgres", "name": "Save to DB", "params": {...}}
        ],
        "connections": {
            "Get Data": [["Save to DB"]]
        }
    },
    "categorization": {"techniques": ["api", "db"], "confidence": 0.9},
    "best_practices": ["Use retry logic", "Add error handling"],
    "coordination_log": [
        {"phase": "discovery", "status": "completed"},
        {"phase": "builder", "status": "completed"}
    ],
    "next_agent": "responder"
}
```

**Key Points:**
- `workflow_json` = The actual workflow being built (MUTATED by each agent)
- `next_agent` = Supervisor's routing decision
- `messages` = Conversation history
- `coordination_log` = Audit trail

---

## How Tools Mutate The Workflow

```python
# In builder node:
workflow = state["workflow_json"]  # Reference to the workflow

# Create tools bound to THIS workflow
tools = create_request_tools(workflow)
# Now when tools are called, they mutate THIS workflow object

# Example: add_node tool
def add_node(type, name, params):
    node = WorkflowNode(type=type, name=name, params=params)
    workflow.nodes.append(node)  # ← MUTATES workflow
    return {"node_id": node.id}

# LLM calls the tool
response = llm_call_tools([add_node, connect_nodes, ...])

# The workflow object is now modified
# state["workflow_json"] reflects the changes
# Next agent sees the updated workflow
```

**Why This Matters:** The SAME workflow object is passed to supervisor, builder, configurator - they all see each other's changes.

---

## Simple Request Example

**Input:**
```json
POST /workflow
{
  "message": "Create workflow: copy file from one location to another"
}
```

**Step-by-step:**

1. **Supervisor** sees empty workflow → sends to builder
2. **Builder** LLM thinks: "Need file copy node"
   - Calls search_nodes("copy") → finds "file_copy" node
   - Calls add_node("file_copy", "Copy File", {...})
   - Calls validate_workflow() → OK
   - Returns: "Added 1 node"
3. **Supervisor** sees workflow has 1 node → Done, send to responder
4. **Responder** serializes and returns:

**Output:**
```json
{
  "name": "Auto-generated",
  "nodes": [
    {
      "type": "file_copy",
      "name": "Copy File",
      "parameters": {"from": "", "to": ""}
    }
  ],
  "connections": [],
  "response": "✅ Built workflow with 1 node"
}
```

---

## File Organization

```
main.py                 ← FastAPI (receives HTTP requests)
  ↓
submain.py              ← WorkflowBuilderOrchestrator (runs the 5-step flow)
  ├─ supervisor.py     ← Agent 1: Routes to next agent
  ├─ discovery.py      ← Agent 2: Analyzes intent
  ├─ builder.py        ← Agent 3: Builds workflow (calls tools)
  ├─ configurator.py   ← Agent 4: Tunes parameters
  └─ responder.py      ← Agent 5: Formats output
  
  📁 tools/            ← Tool factories
  ├─ search_nodes.py
  ├─ add_node.py
  ├─ connect_nodes.py
  ├─ update_parameters.py
  └─ validate_workflow.py
  
  📁 types/            ← Data models
  ├─ nodes.py          (WorkflowNode, WorkflowConnection)
  └─ workflow.py       (SimpleWorkflow)
  
  📁 engines/
  └─ node_search_engine.py  ← Searches available nodes
```

---

## API Endpoints

### POST /workflow
**Request:**
```json
{
  "message": "Build a workflow that...",
  "session_id": "optional_session_id"
}
```

**Response:**
```json
{
  "name": "Auto-generated",
  "nodes": [
    {
      "type": "http",
      "name": "Get Users",
      "parameters": {"url": "https://api.example.com/users"}
    }
  ],
  "edges": [
    {"from": "Get Users", "to": "Save Users"}
  ],
  "response": "✅ Built workflow with 2 nodes",
  "session_id": "optional_session_id"
}
```

### GET /health
Returns: `{"status": "healthy"}`

### GET /node-types
Returns: List of available node types

---

## Critical Design Patterns

### Pattern 1: Per-Request Tool Binding
**Problem:** If tools are created once at startup, they reference stale workflow objects

**Solution:** Create tools in the agent node method, binding them to the workflow in state

```python
# ✅ CORRECT (in builder node)
def builder_node(state):
    workflow = state["workflow_json"]  # Get fresh reference
    tools = create_request_tools(workflow)  # Bind to THIS object
    # Now tool mutations update THIS workflow
    # Next agent sees the changes

# ❌ WRONG (at orchestrator init)
def __init__():
    self.tools = create_tools(workflow)  # Binds to old object
    # Tool mutations don't appear in state
```

### Pattern 2: Deterministic Supervisor
**Problem:** If supervisor uses LLM to decide next agent, it can loop infinitely

**Solution:** Use simple rules based on workflow state

```python
if not workflow.nodes:
    return "builder"  # If no nodes yet, build them
elif needs_config:
    return "configurator"  # If needs tuning, configure
else:
    return "responder"  # Otherwise we're done
```

### Pattern 3: LLM Tool-Calling
**Problem:** How does LLM know what tools exist?

**Solution:** Define tools with clear schemas, LLM knows to call them

```python
tools = [
    Tool(name="add_node", description="Add a node to workflow", 
         args_schema=AddNodeInput),
    Tool(name="connect_nodes", description="Connect two nodes",
         args_schema=ConnectInput),
]

# LLM sees tools and thinks: "I should call add_node with these arguments"
# Tool is executed, result is returned to LLM
# LLM then calls next tool or stops
```

---

## Typical Request Journey

```
1. User: "Create workflow that pulls user data from API and emails it"

2. HTTP POST /workflow arrives at FastAPI

3. orchestrator.process_message(message) called

4. Initial state created:
   - workflow_json: empty workflow
   - messages: [user message]
   - next_agent: None

5. graph execution starts:
   
   ROUND 1: Supervisor
   ├─ Sees empty workflow
   └─ Returns: next_agent = "discovery"
   
   ROUND 2: Discovery
   ├─ LLM analyzes: "API fetching + email notification"
   ├─ Extracts practices: ["Use bearer token for auth", "Add error handling"]
   └─ Returns: categorization + best_practices + updated coordination_log
   
   ROUND 3: Supervisor
   ├─ Sees categorization extracted, but no nodes
   └─ Returns: next_agent = "builder"
   
   ROUND 4: Builder
   ├─ Creates tools bound to workflow
   ├─ LLM calls: search_nodes("API") → HTTP node
   ├─ LLM calls: add_node("http", "Fetch Users", {...})
   ├─ LLM calls: search_nodes("email") → Email node
   ├─ LLM calls: add_node("email", "Send Email", {...})
   ├─ LLM calls: connect_nodes("Fetch Users" → "Send Email")
   ├─ LLM calls: validate_workflow() → OK
   └─ Returns: summary + updated workflow + coordination_log
   
   ROUND 5: Supervisor
   ├─ Sees 2 nodes with connection
   ├─ Checks completeness: satisfied
   └─ Returns: next_agent = "responder"
   
   ROUND 6: Responder
   ├─ Serializes workflow to output format
   ├─ Generates: "✅ Built 2-node workflow"
   └─ Returns: final state + messages
   
6. Graph execution complete, state returned

7. FastAPI endpoint:
   ├─ Extracts nodes[] from workflow
   ├─ Extracts edges[] from workflow
   ├─ Gets last assistant message
   └─ Returns WorkflowResponse JSON

8. HTTP 200 + JSON response sent to client
```

---

## Key Data Types

### WorkflowNode
```python
{
    "type": "http",                    # Node type (http, email, database, etc)
    "name": "Fetch Users",             # Display name
    "nodeId": "uuid-1234",             # Unique ID
    "parameters": {                    # Configuration
        "url": "https://api.example.com/users",
        "method": "GET",
        "headers": {"Authorization": "Bearer token"}
    }
}
```

### WorkflowConnection
```python
{
    "from": "Fetch Users",             # Source node
    "to": "Send Email",                # Target node
    "type": "main"                     # Connection type
}
```

### SimpleWorkflow
```python
{
    "name": "Auto-generated",
    "nodes": [WorkflowNode, WorkflowNode, ...],
    "connections": {
        "Fetch Users": {
            "main": [["Send Email"]]
        }
    }
}
```

---

## What Happens With Errors?

1. **Empty message** → FastAPI returns HTTP 400
2. **Unknown node type** → LLM tries fuzzy matching via resolve_node_type tool
3. **Invalid connection** → validate_workflow tool catches it, builder retries
4. **Validation fails** → Responder still generates response (documents the issue)

---

## Next Steps

1. **Test locally:** 
```bash
python -m uvicorn main:app --reload
curl -X POST http://localhost:8000/workflow \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a simple workflow"}'
```

2. **Add a new tool:** Create factory in `backend/tools/`, add to orchestrator
3. **Add a new agent:** Create in `backend/agents/`, add node to graph
4. **Customize:** Edit prompts in `backend/chains/`, adjust supervisor rules

---

**That's the POC! Simple, focused, 5-step AI orchestration for workflow building.**
