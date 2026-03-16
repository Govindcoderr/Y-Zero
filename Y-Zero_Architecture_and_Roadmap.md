# Y-Zero AI Workflow Builder

## 1. Purpose

Y-Zero is an AI-native workflow design assistant that transforms plain-language requirements into executable n8n-style automation pipelines. It focuses on:
- Conversational input understanding
- Structured workflow graph generation
- Reliable node selection and connection
- Expanded visibility for clients through phase logs and summary

## 2. Goals

### Short-term
- Working local MVP: FastAPI + Streamlit
- Intent filtering via Greeter
- Workflow generation via Builder patterns
- Configurator suggestions

### Mid-term
- Add persistence (workflow history, user sessions)
- Support multiple LLM providers (OpenAI, Anthropic, Groq)
- Add resource-level access controls

### Long-term
- Enterprise-grade workflow orchestrator
- Persistent RAG-based knowledge store for best practices
- Multi-user role support + audit logs
- Direct n8n import/export + production deployment APIs

## 3. High-level architecture

- `streamlit_app.py`: UI for prompt input, workflow visualization, history, export
- `main.py`: FastAPI endpoints `/health`, `/workflow`, plus admin endpoints (`/admin/reindex`, `/admin/es-status`)
  - Loads node definitions from **Elasticsearch** (preferred) via `backend/utils/es_loader.py`
  - Falls back to **in-memory node search** when ES is unavailable
- `submain.py`: WorkflowBuilderOrchestrator with LangGraph pipeline
- `llm_provider.py`: LLM configuration (tool-support model vs fast model)
- `backend/`: agents, tools, engines, state, types, utils

## 3.1 New / Updated Features (since last iteration)

- ✅ **Elasticsearch-backed node catalog**: nodes are now loaded from ES and searchable via full-text fuzzy queries.
- ✅ **Admin endpoints** for operational control: `/admin/reindex` and `/admin/es-status`.
- ✅ **Greeter short-circuit**: handles greetings/out-of-scope queries without generating workflows.
- ✅ **Frontend-friendly response shape**: API now returns `nodes` + `edges` (improved Streamlit UI display).
- ✅ **Resilient fallback**: if ES is down, the system continues using in-memory node search.

## 4. Pipeline (workflow) in detail

### 4.1 Step 0: Request in
API call `POST /workflow` with JSON `{message, session_id}`

### 4.2 Step 1: Greeter stage
- `GreeterAgent` distinguishes intent:
  - `GREETING`, `GUIDE_REQUEST`, `OUT_OF_SCOPE` → short-circuit response (no workflow is built)
  - `WORKFLOW_REQUEST` → continue to supervisor

### 4.3 Step 2: Supervisor
- `SupervisorAgent` chooses next stage by state
- Order:
  1. discovery
  2. builder
  3. configurator
  4. responder

### 4.4 Step 3: Discovery
- `DiscoveryAgent` uses categorization + intent generation + local best practices
- Gains structured intent metadata for builder and UI

### 4.5 Step 4: Builder (core engine)
- `BuilderAgent` uses LLM tool calling with tools:
  - `search_nodes` (NodeSearchEngine fuzzy/shortcut; uses Elasticsearch if available)
  - `add_node` (workflow mutation)
  - `connect_nodes_by_name`/`connect_nodes_by_id`
  - `validate_workflow`
- Builder loop runs max 12 iterations
- Fallback auto-connect to avoid empty connections

### 4.6 Step 5: Configurator
- `ConfiguratorAgent` analyzes node parameters and recommends updates
- At first phase it may only produce textual plan; later can mutate nodes

### 4.7 Step 6: Responder
- Collect final workflow, nodes + edges, message summary
- Return to frontend with structured output and user text

### 4.8 New Node Loading Flow (Elasticsearch)
- On startup, `main.py` loads nodes from Elasticsearch via `backend/utils/es_loader.py`
- If ES is unavailable, node types are still available via in-memory fallback
- `POST /admin/reindex` refreshes the ES index from memory without restarting
- `GET /admin/es-status` reports ES health and indexed node counts

## 5. Data model

### Workflow concepts
- `SimpleWorkflow` (`backend/types/workflow.py`)
  - `name`, `nodes`, `connections`
- `WorkflowNode` has UUID, name, type, coordinates, params
- `WorkflowConnection` has target node, type, index

### State model
- `WorkflowState` (`backend/state/workflow_state.py`): holds messages, workflow_json, coordination_log, next_agent, categorization, best_practices etc.
- Reducers support clean graph merge operations (LangGraph `add_messages`, `merge_logs`).

## 6. Why fuzzy node search (NodeSearchEngine) and not RAG

### Fuzzy matching (n8n-style) advantages
- Node vocab is finite and structured (node definitions in `node_types.json`)
- Allows implicit user phrasing to resolve node names reliably
- Fast deterministic selection (no external embedding retrieval costs)
- Handles alias/displayName/description gracefully via weighted fields

### Why not RAG for node selection
- RAG is best when documents are unstructured or large external corpora; node set is bounded and already in local JSON
- Fewer moving parts: no vector db, no retrieval latency, no staleness overhead
- Easier reproducibility for compliance and debugging

### Where RAG is still relevant
- In future, for `best_practices` or organizational SOP: store process docs and retrieve patterns

## 7. Why LangGraph

### Advantages
- Declarative pipeline graph with nodes + edges, easy to reason
- Per-node logic and conditional transitions (supervisor pattern)
- Built-in state propagation and reducer composition
- Side effect-safe control flow vs monolithic state machine in Python

### Why not alternative frameworks
- Plain `if / elif` sequences are harder to maintain as agents grow
- Celery / Airflow too heavy for request-level orchestration
- LangGraph provides minimal custom stage transitions with strong structure

## 8. Key differentiators vs other workflow products

- Multi-step agent orchestration (not one-shot prompt)
- Tool calling for actual workflow mutation (not just text parsing)
- Intent/greeter gating to reduce cost and stay in-domain
- Phase tracking (`coordination_log`) for audit, debugging, and UX
- Node bank search engine (n8n parity) plus exact/fuzzy handling
- Auto correct / fallback for connections

## 9. Deployment path

### Local dev (current)
- `pip install -r requirements.txt`
- add `.env` with `GROQ_API_KEY` and optional `LLM_MODEL`/`LLM_MODEL_FAST`, `NODES_API_URL`
- run backend: `python main.py`
- run UI: `streamlit run streamlit_app.py`

### Containerization (future)
- Add `Dockerfile` with FastAPI+Streamlit (splits, envs)
- `docker compose` with multi-service support and optional vector store (if RAG added)
- Add healthchecks and config for API keys from secrets

### Cloud
- Azure Web App / Container Apps for backend + static front-end
- Use Azure Key Vault for LLM key
- Add CI/CD via GitHub Actions, unit tests for pipeline nodes and tools

## 10. Growth plan and responsibilities

### Growth benchmarks (MVP → production)
1. Auto-generated workflows with 90% pass validation in first 3 tries
2. Support 15 most critical n8n node families + custom extension API
3. Real-time multi-user sessions with per-session context and rollback
4. Versioned workflow save plus diff/compare
5. Analytics: prompt patterns, node success, failure classification

### Team responsibilities
- Product/PO: define supported workflow types, KPIs
- Core backend: maintain orchestrator, utils, node types, logging
- LLM reliability: prompt updates, model selection, token cost control
- Quality/QA: test grammar, invalid input cases, model fallback (no tool call model)
- DevOps: deployment, secret management, scaling, monitoring

## 11. Future additions

- **Persistence**: user workspace, sessions, workflow history
- **Editor**: Node graph visualization + drag/drop within Streamlit/React
- **Run-time**: option to execute in n8n or emulator (sandbox) API
- **Nodes updates**: live node library from provider APIs + versioning
- **RAG best practices**: knowledge store + retrieval for advanced configurator guidance
- **Security**: auth (OAuth/JWT) + request quota + rate limit

## 12. Client talking points (basic + advanced)

### Basic
- "Describe automation in natural language, get workflow JSON"
- "Greeter stops non-workflow chat and gives quick guide"
- "Flow: understand → analyze → build → configure → response"

### Advanced
- "LLM tool-calling makes the builder iterative and verifiable"
- "Fuzzy search protects from wrong node ids/labels"
- "LangGraph ensures stage-level checkpoints and no endless loops"
- "Full workflow audibility via coordination log and simple to export n8n JSON"

---

## Appendix: Relevant files
- `main.py`
- `submain.py`
- `backend/agents/*.py`
- `backend/tools/*.py`
- `backend/engines/node_search_engine.py`
- `backend/utils/node_normalizer.py`, `node_loader.py`
- `backend/types/workflow.py`
- `streamlit_app.py`
- `llm_provider.py`
