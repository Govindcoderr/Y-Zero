# Y‑Zero: Technical Documentation

> **Goal:** Convert plain-language workflow descriptions into executable **n8n-style workflow graphs** using AI. Y‑Zero is built as a lightweight FastAPI backend with a Streamlit frontend and an AI orchestration pipeline.

---

## 🧩 High-Level Architecture (What & Why)

Y‑Zero is designed to be:

- **Conversational:** Users describe workflows in natural language.
- **Deterministic:** Workflow graph is built using tool-calls (not just freeform text parsing).
- **Extensible:** Node definitions are data-driven and can be updated without changing core logic.
- **Resilient:** Supports a fallback search engine when infrastructure (Elasticsearch) is unavailable.

### Core Functional Layers

1. **User Interface (Streamlit)** – Captures user intent, shows workflow graph results.
2. **API Layer (FastAPI)** – Receives the prompt and returns workflow JSON.
3. **Orchestrator (LangGraph)** – Runs the multi-agent pipeline that turns prompts into workflow graphs.
4. **LLM Provider (Groq by default)** – Generates reasoning, selects nodes, and decides connections.
5. **Node Library + Search (ES / in-memory)** – Provides the universe of available n8n nodes.
6. **Workflow Runtime (SimpleWorkflow model)** – Represents nodes + connections + parameters.

---

## 📦 Tech Stack (What is used + why)

### 🐍 Python (3.8+)
- **Why:** Rapid development, large AI/ML ecosystem, FastAPI + Streamlit compatibility.
- **How:** Main application and orchestration are written in Python.

### 🚀 FastAPI (Backend)
- **Why:** Fast, modern, and has built-in async support + OpenAPI docs.
- **How:** Provides `/health`, `/workflow`, and admin endpoints. Runs the orchestrator.

### 🎛 Streamlit (Frontend)
- **Why:** Quick interactive dashboard for prototyping UI, without separate React stack.
- **How:** Sends workflow prompts to the backend and displays node/edge results + JSON export.

### 🧭 LangGraph (Orchestrator)
- **Why:** Clean declarative agent flow (supervisor → discovery → builder → configurator → responder).
- **How:** Implements stateful pipeline and tools for LLM agent calls.

### 🧠 LLM Provider (Groq by default)
- **Why:** Fast inference (32k context), cost-effective, good for simple prompt chains.
- **How:** Controlled via `llm_provider.py` and environment variable `GROQ_API_KEY`.

### 🔎 Node Search Engine (Elasticsearch + fallback)
- **Why:** Fast fuzzy matching across thousands of node definitions; accurate node resolution.
- **How:** Uses Elasticsearch for search and offers an in-memory fallback if ES is unavailable.

### 🧱 n8n-style Workflow Model
- **Why:** Users expect workflow graphs with nodes + edges + parameters.
- **How:** The system builds a workflow object that can be exported directly as JSON.

---

## 🔄 End‑to‑End Flow (Request → Workflow Response)

### 1) User Input (Streamlit)
- User enters a description (e.g., “Fetch weather every hour and notify Slack”).
- Frontend calls `POST /workflow` on FastAPI.

### 2) FastAPI Receives Request (`main.py`)
- Validates input
- Forwards prompt to `WorkflowBuilderOrchestrator.process_message()`.

### 3) LangGraph Orchestration (`submain.py` - `WorkflowBuilderOrchestrator`)
- Maintains `state` including messages, workflow, categorization, logs.
- Runs a **5-step agent graph**:
  1. **Greeter** – Detects greetings or out-of-scope queries and may short-circuit.
  2. **Supervisor** – Routes into discovery/builder/configurator/responder.
  3. **Discovery** – Extracts workflow intent and best practices.
  4. **Builder** – Uses tool-calling to build nodes/connections.
  5. **Configurator** – Refines node parameters (e.g., API URLs, table names).

### 4) Tool Calls (mutates workflow state)
Tools are concrete functions the LLM can invoke:
- `search_nodes(query)` → finds node candidates (via ES or in-memory)
- `add_node(node_type, label, params)` → adds node object
- `connect_nodes(...)` → creates edges
- `update_parameters(...)` → edits node config
- `validate_workflow()` → checks structure

The workflow object is updated in-place and passed through the pipeline.

### 5) Responder → API Output
- Serializes the workflow into a frontend-friendly JSON format.
- Returns:
  - `nodes` (list of nodes + metadata)
  - `edges` (connections)
  - `response` (assistant text)
  - `session_id` (optional)

### 6) Frontend Displays Result
- Shows nodes / edges tabs.
- Allows JSON download.

---

## 🧠 How Node Selection Works (New Feature: Elasticsearch + Dynamic Load)

### Node Store Source Options
1. **Elasticsearch (preferred)**
   - Nodes are stored in ES in index `yzero_nodes` (configurable via `ES_NODE_INDEX`).
   - Each document contains a base64-encoded `_raw` payload with the full node definition.
   - Allows fast fuzzy search with scoring, auto-fallback, and live updates.
2. **In-memory fallback** (when ES is unavailable)
   - Uses the original `sublimeSearch` style fuzzy matching.
   - Ensures the system still works without ES.

### How it works (runtime)
1. **Startup** (`main.py` lifespan)
   - Calls `load_nodes_from_es()` to fetch every node definition.
   - Initializes the `WorkflowBuilderOrchestrator` with those nodes.
   - Calls `reindex_all()` to ensure ES index matches in-memory nodes.
2. **Search**
   - `NodeSearchEngine.search_by_name()` uses ES `multi_match` query with fuzziness.
   - `NodeSearchEngine.resolve_node_type()` returns best match or fallback to `HTTP REQUEST`.
3. **Live updates**
   - `NodeSearchEngine.add_or_update_node()` can be called to add new nodes dynamically.
   - `NodeSearchEngine.delete_node()` removes deprecated nodes.
4. **Admin endpoints**
   - `POST /admin/reindex` → re-sync nodes into ES without restart.
   - `GET /admin/es-status` → check ES connectivity and indexed count.

---

## 📌 Key Components & Their Roles

### `streamlit_app.py` (UI)
- Captures user prompt
- Shows conversation history
- Displays generated workflow nodes + edges
- Exports JSON

### `main.py` (Backend API)
- FastAPI app with `/workflow`, `/health`, and admin endpoints
- Loads node definitions from Elasticsearch and initializes orchestrator
- Handles greeter short-circuit responses (non-workflow chat)

### `submain.py` (Workflow Orchestrator)
- Runs the LangGraph workflow
- Maintains `WorkflowState` (messages, workflow_json, logs, etc.)

### `backend/agents/*` (LangGraph Agents)
- **greeter.py**: Detects greetings/out-of-scope
- **supervisor.py**: Chooses the next phase
- **discovery.py**: Classifies intent
- **builder.py**: Calls tools to build graph
- **configurator.py**: Adjusts parameters

### `backend/tools/*` (Tool Functions)
- `search_nodes.py` — find node candidates
- `add_node.py` — append node
- `connect_nodes.py` — create edges
- `update_parameters.py` — set node params
- `validate_workflow.py` — check graph validity

### `backend/engines/node_search_engine.py` (Search Engine)
- Provides unified search interface (ES + fallback)
- Exposes `resolve_node_type()` used by LLM agent

### `backend/utils/*`
- `node_loader.py` — (legacy) load node types
- `node_normalizer.py` — normalize nodes to consistent schema
- `es_loader.py` — load nodes from Elasticsearch
- `es_indexer.py` — reindex utility (run at startup + via admin endpoint)

---

## 🔧 Configuration & Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `GROQ_API_KEY` | LLM API key | `sk-xxx` |
| `ELASTICSEARCH_URL` | ES endpoint | `http://localhost:9200` |
| `ELASTICSEARCH_USER` | ES basic auth user (optional) | `elastic` |
| `ELASTICSEARCH_PASSWORD` | ES basic auth password (optional) | `changeme` |
| `ES_NODE_INDEX` | Elasticsearch index name | `yzero_nodes` |
| `NODES_API_URL` | (legacy) external node definitions URL | `https://.../nodes.json` |

> **Note:** If ES is not running, the system falls back to in-memory search.

---

## 🧭 Running the System (Local Dev)

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Set environment variables
Create `.env` with:
```env
GROQ_API_KEY=YOUR_KEY
ELASTICSEARCH_URL=http://localhost:9200
```

### 3) Run
**Backend:**
```bash
python main.py
```

**Frontend:**
```bash
streamlit run streamlit_app.py
```

**Alternative (single command):**
```bash
python run_all.py
```

---

## ✅ New / Updated Features (Since previous version)

### ✅ Elasticsearch-backed Node Catalog
- Nodes are now loaded from an Elasticsearch index instead of a local JSON file.
- Enables fast fuzzy search, large scale catalogs, and live updates.
- Includes resilience: if ES cannot be reached, system falls back to in-memory search.

### ✅ Admin Reindex Endpoint
- `POST /admin/reindex` triggers an ES sync without restarting the server.
- `GET /admin/es-status` provides health and node count info.

### ✅ Improved Response Shape (Frontend-friendly)
- API now returns `nodes` + `edges` with better metadata (`NodeOut` / `EdgeOut`).
- Streamlit UI now displays full edge list and node metadata.

### ✅ Greeter Short‑Circuit
- Friendly chat or out-of-scope questions are handled without building a workflow.
- Response still returns consistent schema, with empty workflow and just `response` text.

---

## 📌 Project Flow (High‑Level Diagram)

```
[User] → (Streamlit UI)
          → POST /workflow
             (FastAPI)
             → WorkflowBuilderOrchestrator
                → Greeter (short-circuit?)
                → Supervisor (route phases)
                → Discovery (intent classification)
                → Builder (tools + LLM → mutate workflow)
                → Configurator (tune nodes)
                → Responder (serialize output)
          ← Response (Nodes + Edges)
          ← Display in UI / Export JSON
```

### Detailed Sequence (Flow)

1. **User enters prompt** → Streamlit calls `/workflow`.
2. **FastAPI** loads nodes from ES → starts orchestrator.
3. **Orchestrator** creates a fresh `state` and pushes user message.
4. **Greeter** checks if the prompt is a greeting / out-of-scope.
   - If yes: returns text response only.
   - If no: proceeds.
5. **Supervisor** chooses the next agent (discovery/builder/configurator/responder) based on state.
6. **Discovery** classifies intent (API call, email, etc.) and saves metadata.
7. **Builder** uses the LLM + tools to mutate workflow (nodes + edges).
8. **Configurator** updates node parameters and ensures links are valid.
9. **Responder** serializes the final `SimpleWorkflow` into API response.
10. **Streamlit** renders the graph and allows JSON download.

---

## 🧩 How to Add / Update Nodes (New Integrations)

### Option A: Add via Elasticsearch (recommended)
1. Insert a new node document into the `yzero_nodes` index.
   - Store full node definition in `_raw` as base64-encoded JSON.
2. Call `POST /admin/reindex` (or restart the server).
3. The search engine refreshes and the new node becomes available.

### Option B: Use `node_types.json` (legacy)
- Existing node definitions in `node_types.json` are still supported (if loaded).
- Replace with updated file and restart.

---

## 🔍 Troubleshooting

### ❌ API returns `Orchestrator not initialized`
- Ensure `GROQ_API_KEY` is set.
- Confirm ES is reachable (or allow fallback by not setting ES env variables).

### ❌ Search returns wrong node
- Confirm nodes are indexed in ES and re-run `/admin/reindex`.

### 🧠 LLM generates incorrect workflow
- Update prompts or templates in `backend/chains/*`.
- Extend `backend/agents` logic to constrain tool calls.

---

## 📌 Where to Look for Core Logic

| Area | Files / Folders |
|------|----------------|
| API layer | `main.py` |
| Orchestrator | `submain.py` |
| Agents | `backend/agents/*.py` |
| Tools | `backend/tools/*.py` |
| Node search | `backend/engines/node_search_engine.py` |
| Node loading | `backend/utils/es_loader.py` |
| Streamlit UI | `streamlit_app.py` |

---

## ✅ Quick “What is Y‑Zero?” Summary

Y‑Zero is an **AI-powered workflow graph generator**. You tell it in plain English what you want to automate, and it builds an **n8n-style workflow** (nodes + connections + parameters) using a multi-agent orchestration pipeline and a searchable library of node types.

It is intended for quick prototyping and experimentation, with a path to production via persistent stores (Elasticsearch), clear tool boundaries, and a consumable JSON workflow output.

---

*Document last updated: March 16, 2026*
