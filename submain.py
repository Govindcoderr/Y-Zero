
# # submain.py
# """
# Key fixes applied:
# 1. Tools are now bound to the workflow INSTANCE (not state dict) so mutations persist
# 2. Tools are recreated each request so they bind to the fresh workflow object
# 3. WorkflowState no longer tries to serialize dataclasses through LangGraph checkpointer
# 4. Supervisor uses deterministic routing instead of LLM (avoids infinite loops)
# 5. Messages in state are handled as dicts consistently
# 6. coordination_log uses a custom merge reducer (not add_messages)
# 7. `next_agent` is stored in state and read by the conditional edge lambda
# """

# from langgraph.graph import StateGraph, END
# from llm_provider import get_llm
# from typing import Dict, Any, Optional
# from backend.state.workflow_state import WorkflowState, create_initial_state
# from backend.engines.node_search_engine import NodeSearchEngine
# from backend.agents.supervisor import SupervisorAgent
# from backend.agents.discovery import DiscoveryAgent
# from backend.agents.builder import BuilderAgent
# from backend.agents.configurator import ConfiguratorAgent
# from backend.tools.search_nodes import create_search_nodes_tool
# from backend.tools.get_node_details import create_get_node_details_tool
# from backend.tools.add_node import create_add_node_tool
# from backend.tools.connect_nodes import create_connect_nodes_tool
# from backend.tools.update_parameters import create_update_parameters_tool
# from backend.tools.validate_workflow import create_validate_workflow_tool
# from backend.tools.resolve_node_type import create_resolve_node_type_tool
# from backend.types.coordination import CoordinationLogEntry
# from backend.types.workflow import SimpleWorkflow
# from datetime import datetime
# import json


# class WorkflowBuilderOrchestrator:
#     """Main orchestrator for workflow building"""

#     def __init__(self, api_key: str, node_types: list):
#         self.llm = get_llm()
#         self.node_types = node_types

#         # Initialize search engine (stateless - can be shared)
#         self.search_engine = NodeSearchEngine(node_types)
#         print(f"✅ Node search engine initialized with {len(node_types)} node types")

#         # Agents that don't depend on per-request workflow state
#         self.supervisor = SupervisorAgent(self.llm)
#         self.discovery = DiscoveryAgent(self.llm)

#         # Build graph (builder/configurator tools are recreated per request)
#         self.graph = self._build_graph()
#         print("✅ LangGraph workflow graph compiled successfully")

#     def _create_request_tools(self, workflow: SimpleWorkflow):
#         """
#         Create tools bound to a specific workflow instance.
#         Must be called per-request since tools mutate the workflow object.

#         Builder tools: search, inspect, add nodes, connect nodes
#         Configurator tools: update parameters, validate
#         """
#         # connect_nodes returns a tuple of (by_name_tool, by_id_tool)
#         connect_by_name, connect_by_id = create_connect_nodes_tool(workflow)

#         # validate_workflow is shared - builder uses it to verify, configurator uses it too
#         validate_tool = create_validate_workflow_tool(workflow)

#         builder_tools = [
#             create_resolve_node_type_tool(self.search_engine),  # FIRST: validate/resolve node types
#             create_search_nodes_tool(self.search_engine),
#             create_get_node_details_tool(self.search_engine),
#             create_add_node_tool(workflow, self.search_engine),  # auto-resolves unknown types
#             connect_by_name,   # primary - LLM uses node names
#             connect_by_id,     # fallback - LLM uses UUIDs from add_node response
#             validate_tool,     # LLM can call this to verify connections
#         ]
#         configurator_tools = [
#             create_update_parameters_tool(self.llm, self.search_engine, workflow),
#             validate_tool,     # reuse same instance
#         ]
#         return builder_tools, configurator_tools

#     def _build_graph(self):
#         """Build the LangGraph state graph"""

#         graph = StateGraph(WorkflowState)

#         graph.add_node("supervisor", self._supervisor_node)
#         graph.add_node("discovery", self._discovery_node)
#         graph.add_node("builder", self._builder_node)
#         graph.add_node("configurator", self._configurator_node)
#         graph.add_node("responder", self._responder_node)

#         graph.set_entry_point("supervisor")

#         # Route from supervisor based on next_agent field in state
#         graph.add_conditional_edges(
#             "supervisor",
#             lambda state: state.get("next_agent", "responder"),
#             {
#                 "discovery": "discovery",
#                 "builder": "builder",
#                 "configurator": "configurator",
#                 "responder": "responder",
#             },
#         )

#         # After each phase, return to supervisor for re-evaluation
#         graph.add_edge("discovery", "supervisor")
#         graph.add_edge("builder", "supervisor")
#         graph.add_edge("configurator", "supervisor")
#         graph.add_edge("responder", END)

#         return graph.compile()

#     # -------------------------------------------------------------------------
#     # Graph node implementations
#     # -------------------------------------------------------------------------

#     async def _supervisor_node(self, state: WorkflowState) -> Dict[str, Any]:
#         """Decide which agent acts next"""
#         next_agent = await self.supervisor.decide_next_agent(state)
#         print(f"🔀 Supervisor → {next_agent}")
#         return {"next_agent": next_agent}

#     async def _discovery_node(self, state: WorkflowState) -> Dict[str, Any]:
#         """Run discovery agent"""
#         user_message = self._extract_last_user_message(state)
#         print(f"🔍 Discovery agent analyzing: {user_message[:60]}...")

#         result = await self.discovery.analyze(user_message)

#         log_entry = CoordinationLogEntry(
#             phase="discovery",
#             status="completed",
#             timestamp=datetime.now().timestamp(),
#             summary=result["summary"],
#             metadata={
#                 "techniques": [
#                     t.value if hasattr(t, "value") else str(t)
#                     for t in result["categorization"].techniques
#                 ],
#                 "confidence": result["categorization"].confidence,
#             },
#         )

#         return {
#             "categorization": result["categorization"],
#             "best_practices": result["best_practices"],
#             "coordination_log": [log_entry],
#         }

#     async def _builder_node(self, state: WorkflowState) -> Dict[str, Any]:
#         """Run builder agent using workflow-bound tools"""
#         print("🏗️  Builder agent building workflow...")
#         workflow = state["workflow_json"]

#         builder_tools, _ = self._create_request_tools(workflow)
#         builder = BuilderAgent(self.llm, builder_tools, self.search_engine)

#         result = await builder.build_workflow(state)

#         log_entry = CoordinationLogEntry(
#             phase="builder",
#             status="completed",
#             timestamp=datetime.now().timestamp(),
#             summary=result["summary"],
#             metadata={"nodes_added": result["nodes_added"]},
#         )

#         print(f"   → {result['nodes_added']} nodes in workflow")
#         return {"coordination_log": [log_entry]}

#     async def _configurator_node(self, state: WorkflowState) -> Dict[str, Any]:
#         """Run configurator agent"""
#         print("⚙️  Configurator agent configuring nodes...")
#         workflow = state["workflow_json"]

#         _, configurator_tools = self._create_request_tools(workflow)
#         configurator = ConfiguratorAgent(self.llm, configurator_tools)

#         result = await configurator.configure_workflow(state)

#         log_entry = CoordinationLogEntry(
#             phase="configurator",
#             status="completed",
#             timestamp=datetime.now().timestamp(),
#             summary=result["summary"],
#             metadata={"nodes_configured": result["nodes_configured"]},
#         )

#         print(f"   → {result['nodes_configured']} nodes configured")
#         return {"coordination_log": [log_entry]}

#     async def _responder_node(self, state: WorkflowState) -> Dict[str, Any]:
#         """Generate final response"""
#         workflow = state["workflow_json"]

#         node_lines = []
#         for node in workflow.nodes:
#             node_lines.append(f"  • {node.name} ({node.type})")
#             if node.name in workflow.connections:
#                 for conn_type, conn_list in workflow.connections[node.name].items():
#                     for conn_array in conn_list:
#                         for conn in conn_array:
#                             node_lines.append(f"      → {conn.node}")

#         connection_count = sum(
#             len(conn_array[0]) if conn_array else 0
#             for connections in workflow.connections.values()
#             for conn_array in connections.values()
#         )

#         response = (
#             f"✅ Workflow '{workflow.name}' has been built successfully!\n\n"
#             f"📊 Summary:\n"
#             f"  - {len(workflow.nodes)} nodes added\n"
#             f"  - {connection_count} connections created\n\n"
#             f"🔗 Workflow structure:\n"
#             + ("\n".join(node_lines) if node_lines else "  (empty workflow)")
#             + "\n\nThe workflow is ready to use!"
#         )

#         print(f"✅ Responder: workflow complete with {len(workflow.nodes)} nodes")
#         return {"messages": [{"role": "assistant", "content": response}]}

#     # -------------------------------------------------------------------------
#     # Helpers
#     # -------------------------------------------------------------------------

#     def _extract_last_user_message(self, state: Dict[str, Any]) -> str:
#         messages = state.get("messages", [])
#         if not messages:
#             return ""
#         last = messages[-1]
#         if isinstance(last, dict):
#             return last.get("content") or last.get("text") or ""
#         return getattr(last, "content", None) or str(last)

#     async def process_message(
#         self, user_message: str, state: Optional[WorkflowState] = None
#     ) -> WorkflowState:
#         """
#         Process a user message and build a workflow.

#         Args:
#             user_message: Natural language description of the desired workflow
#             state: Optional existing state for multi-turn conversations

#         Returns:
#             Final WorkflowState after graph execution
#         """
#         if state is None:
#             state = create_initial_state()

#         # Append user message to history
#         state["messages"].append({"role": "user", "content": user_message})

#         print(f"\n{'='*60}")
#         print(f"Processing: {user_message[:80]}...")
#         print(f"{'='*60}")

#         # Run the graph
#         result = await self.graph.ainvoke(state)

#         return result





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
from backend.types.coordination import CoordinationLogEntry
from backend.types.workflow import SimpleWorkflow
from datetime import datetime
import json


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
        self.supervisor = SupervisorAgent(self.llm_fast)
        self.discovery = DiscoveryAgent(self.llm_fast)

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
            create_resolve_node_type_tool(self.search_engine),  # FIRST: validate/resolve node types
            create_search_nodes_tool(self.search_engine),
            create_get_node_details_tool(self.search_engine),
            create_add_node_tool(workflow, self.search_engine),  # auto-resolves unknown types
            connect_by_name,   # primary - LLM uses node names
            connect_by_id,     # fallback - LLM uses UUIDs from add_node response
            validate_tool,     # LLM can call this to verify connections
        ]
        configurator_tools = [
            create_update_parameters_tool(self.llm, self.search_engine, workflow),
            validate_tool,     # reuse same instance
        ]
        return builder_tools, configurator_tools

    def _build_graph(self):
        """Build the LangGraph state graph"""

        graph = StateGraph(WorkflowState)

        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("discovery", self._discovery_node)
        graph.add_node("builder", self._builder_node)
        graph.add_node("configurator", self._configurator_node)
        graph.add_node("responder", self._responder_node)

        graph.set_entry_point("supervisor")

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

    async def _builder_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Run builder agent using workflow-bound tools"""
        print("🏗️  Builder agent building workflow...")
        workflow = state["workflow_json"]

        builder_tools, _ = self._create_request_tools(workflow)
        builder = BuilderAgent(self.llm, builder_tools, self.search_engine)

        result = await builder.build_workflow(state)

        log_entry = CoordinationLogEntry(
            phase="builder",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=result["summary"],
            metadata={"nodes_added": result["nodes_added"]},
        )

        print(f"   → {result['nodes_added']} nodes in workflow")
        return {"coordination_log": [log_entry]}

    async def _configurator_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Run configurator agent"""
        print("⚙️  Configurator agent configuring nodes...")
        workflow = state["workflow_json"]

        _, configurator_tools = self._create_request_tools(workflow)
        configurator = ConfiguratorAgent(self.llm, configurator_tools)

        result = await configurator.configure_workflow(state)

        log_entry = CoordinationLogEntry(
            phase="configurator",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=result["summary"],
            metadata={"nodes_configured": result["nodes_configured"]},
        )

        print(f"   → {result['nodes_configured']} nodes configured")
        return {"coordination_log": [log_entry]}

    async def _responder_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate final response"""
        workflow = state["workflow_json"]

        node_lines = []
        for node in workflow.nodes:
            node_lines.append(f"  • {node.name} ({node.type})")
            if node.name in workflow.connections:
                for conn_type, conn_list in workflow.connections[node.name].items():
                    for conn_array in conn_list:
                        for conn in conn_array:
                            node_lines.append(f"      → {conn.node}")

        connection_count = sum(
            len(conn_array[0]) if conn_array else 0
            for connections in workflow.connections.values()
            for conn_array in connections.values()
        )

        response = (
            f"✅ Workflow '{workflow.name}' has been built successfully!\n\n"
            f"📊 Summary:\n"
            f"  - {len(workflow.nodes)} nodes added\n"
            f"  - {connection_count} connections created\n\n"
            f"🔗 Workflow structure:\n"
            + ("\n".join(node_lines) if node_lines else "  (empty workflow)")
            + "\n\nThe workflow is ready to use!"
        )

        print(f"✅ Responder: workflow complete with {len(workflow.nodes)} nodes")
        return {"messages": [{"role": "assistant", "content": response}]}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _extract_last_user_message(self, state: Dict[str, Any]) -> str:
        messages = state.get("messages", [])
        if not messages:
            return ""
        last = messages[-1]
        if isinstance(last, dict):
            return last.get("content") or last.get("text") or ""
        return getattr(last, "content", None) or str(last)

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