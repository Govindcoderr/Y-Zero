
# submain.py
"""
Key fixes applied:
1. Tools are now bound to the workflow INSTANCE (not state dict) so mutations persist
2. Tools are recreated each request so they bind to the fresh workflow object
3. WorkflowState no longer tries to serialize dataclasses through LangGraph checkpointer
4. Supervisor uses deterministic routing instead of LLM (avoids infinite loops)
5. Messages in state are handled as dicts consistently
6. coordination_log uses a custom merge reducer (not add_messages)
7. `next_agent` is stored in state and read by the conditional edge lambda
"""

from langgraph.graph import StateGraph, END
from backend.agents.greeter import GreeterAgent
from llm_provider import get_llm, get_llm_no_tools
from typing import Dict, Any, Optional
from backend.state.workflow_state import WorkflowState, create_initial_state
from backend.engines.node_search_engine import NodeSearchEngine
from backend.agents.supervisor import SupervisorAgent
from backend.agents.discovery import DiscoveryAgent
from backend.agents.builder import BuilderAgent
from backend.agents.configurator import ConfiguratorAgent
from backend.tools.search_nodes import create_search_nodes_tool
from backend.tools.get_node_details import create_get_node_details_tool
from backend.tools.add_node import create_add_node_tool
from backend.tools.connect_nodes import create_connect_nodes_tool
from backend.tools.update_parameters import create_update_parameters_tool
from backend.tools.validate_workflow import create_validate_workflow_tool
from backend.tools.resolve_node_type import create_resolve_node_type_tool
from backend.types.coordination import CoordinationLogEntry, create_builder_metadata
from backend.types.workflow import SimpleWorkflow
from datetime import datetime
import json
from backend.tracker.pipeline_tracker import emit, emit_done, StepStatus
from backend.agents.responder import ResponderAgent 

class WorkflowBuilderOrchestrator:
    """Main orchestrator for workflow building"""

    def __init__(self, api_key: str, node_types: list):
        self.llm = get_llm()              # tool-calling capable (for builder/configurator)
        self.llm_fast = get_llm_no_tools()   # plain LLM (for discovery/supervisor)
        self.node_types = node_types

        # Initialize search engine (stateless - can be shared)
        self.search_engine = NodeSearchEngine(node_types)
        print(f"✅ Node search engine initialized with {len(node_types)} node types")

        # Agents that don't depend on per-request workflow state
        self.greeter = GreeterAgent(self.llm_fast)  
        self.supervisor = SupervisorAgent(self.llm_fast)
        self.discovery = DiscoveryAgent(self.llm_fast)
        self.responder_agent = ResponderAgent(self.llm_fast)

        # Build graph (builder/configurator tools are recreated per request)
        self.graph = self._build_graph()
        print("✅ LangGraph workflow graph compiled successfully")

    def _create_request_tools(self, workflow: SimpleWorkflow):
        """
        Create tools bound to a specific workflow instance.
        Must be called per-request since tools mutate the workflow object.

        Builder tools: search, inspect, add nodes, connect nodes
        Configurator tools: update parameters, validate
        """
        # connect_nodes returns a tuple of (by_name_tool, by_id_tool)
        connect_by_name, connect_by_id = create_connect_nodes_tool(workflow)

        # validate_workflow is shared - builder uses it to verify, configurator uses it too
        validate_tool = create_validate_workflow_tool(workflow)

        builder_tools = [
            create_search_nodes_tool(self.search_engine),        # search to find exact node names
            create_add_node_tool(workflow, self.search_engine),  # auto-resolves unknown types
            connect_by_name,   # primary - LLM uses node names
            connect_by_id,     # fallback - LLM uses UUIDs from add_node response
            validate_tool,     # call ONCE at the end
        ]
        # configurator_tools = [ (old way with llm and search_engine passed in )
        #     create_update_parameters_tool(self.llm, self.search_engine, workflow),
        #     validate_tool,     # reuse same instance
        # ]

        # _create_request_tools mein configurator_tools update karo:
        configurator_tools = [
            create_update_parameters_tool(workflow),   # ← sirf workflow pass karo, llm aur search_engine nahi
            validate_tool,
        ]


        return builder_tools, configurator_tools

    def _build_graph(self):
        """Build the LangGraph state graph"""

        graph = StateGraph(WorkflowState)

        graph.add_node("greeter", self._greeter_node)      
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("discovery", self._discovery_node)
        graph.add_node("builder", self._builder_node)
        graph.add_node("configurator", self._configurator_node)
        graph.add_node("responder", self._responder_node)

        graph.set_entry_point("greeter")

        # ── Greeter routing .....────
        # If should_proceed=True → go to supervisor (normal workflow pipeline)
        # If should_proceed=False → END (greeter already responded)
        graph.add_conditional_edges(
            "greeter",
            lambda state: "supervisor" if state.get("greeter_proceed", False) else END,
            {
                "supervisor": "supervisor",
                END: END,
            },
        )

        # Route from supervisor based on next_agent field in state
        graph.add_conditional_edges(
            "supervisor",
            lambda state: state.get("next_agent", "responder"),
            {
                "discovery": "discovery",
                "builder": "builder",
                "configurator": "configurator",
                "responder": "responder",
            },
        )

        # After each phase, return to supervisor for re-evaluation
        graph.add_edge("discovery", "supervisor")
        graph.add_edge("builder", "supervisor")
        graph.add_edge("configurator", "supervisor")
        graph.add_edge("responder", END)

        return graph.compile()

    # -------------------------------------------------------------------------
    # Graph node implementations
    # -------------------------------------------------------------------------

    
    async def _greeter_node(self, state: WorkflowState) -> Dict[str, Any]:
        """
        FIRST agent in the pipeline.
        Detects intent and either:
          - Responds directly (greetings / guide / out-of-scope) → END
          - Passes control to supervisor → workflow pipeline
        """
        user_message = self._extract_last_user_message(state)
        print(f"🤝 Greeter agent checking: {user_message[:60]}...")

        result = await self.greeter.handle(user_message)
        intent = result["intent"]
        should_proceed = result["should_proceed"]

        if should_proceed:
            # Real workflow request → continue pipeline
            print(f"   → Intent: {intent} — proceeding to workflow pipeline")
            return {
                "greeter_proceed": True,
                "greeter_intent": intent,
            }
        else:
            # Greeting / Guide / Out-of-scope → respond and stop
            reply = result["response"]
            print(f"   → Intent: {intent} — greeter responding, pipeline stopped")
            return {
                "greeter_proceed": False,
                "greeter_intent": intent,
                "messages": [{"role": "assistant", "content": reply}],
            }


    async def _supervisor_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Decide which agent acts next"""
        next_agent = await self.supervisor.decide_next_agent(state)
        print(f"🔀 Supervisor → {next_agent}")
        return {"next_agent": next_agent}

    async def _discovery_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Run discovery agent"""
        user_message = self._extract_last_user_message(state)
        print(f"🔍 Discovery agent analyzing: {user_message[:60]}...")

        result = await self.discovery.analyze(user_message)

        log_entry = CoordinationLogEntry(
            phase="discovery",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=result["summary"],
            metadata={
                "techniques": [
                    t.value if hasattr(t, "value") else str(t)
                    for t in result["categorization"].techniques
                ],
                "confidence": result["categorization"].confidence,
            },
        )

        return {
            "categorization": result["categorization"],
            "best_practices": result["best_practices"],
            "coordination_log": [log_entry],
        }

    async def _builder_node(self, state):
        """
        Run builder agent — writes `output` to its coordination log entry
        so the Responder can read a human-readable workflow summary.
        """
        print("Building workflow...")
        workflow = state["workflow_json"]
    
        if workflow.nodes:
            return {
                "coordination_log": [],
                # no-op if already built
            }
    
        builder_tools, _ = self._create_request_tools(workflow)
        builder = BuilderAgent(self.llm, builder_tools, self.search_engine)
        result = await builder.build_workflow(state)
    
        # ── Build human-readable workflow description for Responder ──────────
        node_chain = " → ".join(n.name for n in workflow.nodes)
        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )
        builder_output = (
            f"{len(workflow.nodes)} nodes created: {node_chain}\n"
            f"{connection_count} connection(s) established."
        )
    
        log_entry = CoordinationLogEntry(
            phase="builder",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=result["summary"],
            output=builder_output,                         # ← NEW: Responder reads this
            metadata=create_builder_metadata(
                nodes_created=len(workflow.nodes),
                connections_created=connection_count,
                node_names=[n.name for n in workflow.nodes],
            ),
        )
    
        print(f"   → {result['nodes_added']} nodes in workflow")
        return {"coordination_log": [log_entry]}

    async def _configurator_node(self, state):
        """
        Run configurator agent — writes `output` (setup instructions) to its
        coordination log entry so the Responder includes them in its reply.
        """
        print("Configuring nodes...")
        workflow = state["workflow_json"]
    
        _, configurator_tools = self._create_request_tools(workflow)
        configurator = ConfiguratorAgent(self.llm, configurator_tools)
        result = await configurator.configure_workflow(state)
    
        # The configurator summary IS the setup instructions text
        configurator_output = result.get("summary", "")
    
        from backend.types.coordination import CoordinationLogEntry, create_configurator_metadata
        from datetime import datetime
    
        log_entry = CoordinationLogEntry(
            phase="configurator",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=f"{result['nodes_configured']} nodes configured",
            output=configurator_output,                    # ← NEW: Responder reads this
            metadata=create_configurator_metadata(
                nodes_configured=result["nodes_configured"],
                has_setup_instructions=bool(configurator_output),
            ),
        )
    
        print(f"   → {result['nodes_configured']} nodes configured")
        return {"coordination_log": [log_entry]}
    


    async def _responder_node(self, state):
        """
        Generate final response using the dedicated ResponderAgent.
    
        The ResponderAgent:
        - Reads the coordination log for builder/configurator outputs
        - Reads workflow state for node count / structure
        - Applies n8n-style communication rules (no emojis, concise, setup instructions)
        - Returns a clean, user-facing string
        """
        from backend.agents.responder import ResponderAgent
    
        # Lazy init (or use self.responder_agent if pre-created in __init__)
        responder = ResponderAgent(self.llm_fast)
        response_text = await responder.generate_response(state)
    
        print(f"Responder: {response_text[:100]}...")
        return {"messages": [{"role": "assistant", "content": response_text}]}
    

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    # def _extract_last_user_message(self, state: Dict[str, Any]) -> str:
    #     messages = state.get("messages", [])
    #     if not messages:
    #         return ""
    #     last = messages[-1]
    #     if isinstance(last, dict):
    #         return last.get("content") or last.get("text") or ""
    #     return getattr(last, "content", None) or str(last)

    def _extract_last_user_message(self, state: Dict[str, Any]) -> str:
        messages = state.get("messages", [])
        if not messages:
            return ""
        # Walk backwards to find last user message
        for msg in reversed(messages):
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    return msg.get("content", "")
            else:
                if getattr(msg, "type", "") == "human":
                    return getattr(msg, "content", "")
        return ""

    async def process_message(
        self, user_message: str, state: Optional[WorkflowState] = None
    ) -> WorkflowState:
        """
        Process a user message and build a workflow.

        Args:
            user_message: Natural language description of the desired workflow
            state: Optional existing state for multi-turn conversations

        Returns:
            Final WorkflowState after graph execution
        """
        if state is None:
            state = create_initial_state()

        # Append user message to history
        state["messages"].append({"role": "user", "content": user_message})

        print(f"\n{'='*60}")
        print(f"Processing: {user_message[:80]}...")
        print(f"{'='*60}")

        # Run the graph
        result = await self.graph.ainvoke(state)

        return result