# submain.py
from langgraph.graph import StateGraph, END
from llm_provider import get_llm
from typing import Dict, Any
from backend.state.workflow_state import WorkflowState, create_initial_state
from backend.engines.node_search_engine import NodeSearchEngine
from backend.agents.supervisor import SupervisorAgent
from backend.agents.discovery import DiscoveryAgent
from backend.agents.builder import BuilderAgent
from backend.agents.configurator import ConfiguratorAgent
from backend.tools.search_nodes import create_search_nodes_tool
from backend.tools.get_node_details  import create_get_node_details_tool
from backend.tools.add_node import create_add_node_tool
from backend.tools.connect_nodes import create_connect_nodes_tool
from backend.tools.update_parameters import create_update_parameters_tool
from backend.tools.validate_workflow import create_validate_workflow_tool
from backend.types.coordination import CoordinationLogEntry
from datetime import datetime
import json

class WorkflowBuilderOrchestrator:
    """Main orchestrator for workflow building"""
    
    def __init__(self, api_key: str, node_types: list):
        # Initialize LLM using Groq
        self.llm = get_llm()
        
        # Initialize search engine
        self.search_engine = NodeSearchEngine(node_types)
        print("Node search engine initialized with 31 main", len(node_types), "node types")
        
        # Create tools
        self.builder_tools = [
            create_search_nodes_tool(self.search_engine),
            create_get_node_details_tool(self.search_engine),
            create_add_node_tool(),
            create_connect_nodes_tool(),
        ]
        print("Builder tools created:40 ", [tool.name for tool in self.builder_tools])
        self.configurator_tools = [
            create_update_parameters_tool(self.llm, self.search_engine),
            create_validate_workflow_tool(),
        ]
        print("Configurator tools created: 41  ", [tool.name for tool in self.configurator_tools])
        # Initialize agents
        self.supervisor = SupervisorAgent(self.llm)
        self.discovery = DiscoveryAgent(self.llm)
        self.builder = BuilderAgent(self.llm, self.builder_tools, self.search_engine)
        self.configurator = ConfiguratorAgent(self.llm, self.configurator_tools)
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph state graph"""
        
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("discovery", self._discovery_node)
        workflow.add_node("builder", self._builder_node)
        workflow.add_node("configurator", self._configurator_node)
        workflow.add_node("responder", self._responder_node)
        
        # Add edges
        workflow.set_entry_point("supervisor")
        
        # Conditional routing from supervisor
        workflow.add_conditional_edges(
            "supervisor",
            lambda state: state.get("next_agent", "responder"),
            {
                "discovery": "discovery",
                "builder": "builder",
                "configurator": "configurator",
                "responder": "responder",
            }
        )
        
        # After each agent, go back to supervisor
        workflow.add_edge("discovery", "supervisor")
        workflow.add_edge("builder", "supervisor")
        workflow.add_edge("configurator", "supervisor")
        workflow.add_edge("responder", END)
        
        return workflow.compile()
    
    async def _supervisor_node(self, state: WorkflowState) -> WorkflowState:
        """Supervisor agent node"""
        next_agent = await self.supervisor.decide_next_agent(state)
        return {"next_agent": next_agent}
    
    async def _discovery_node(self, state: WorkflowState) -> WorkflowState:
        """Discovery agent node"""
        # Get user message
        user_message = state["messages"][-1].content if state["messages"] else ""
        
        # Analyze
        result = await self.discovery.analyze(user_message)
        
        # Update state
        log_entry = CoordinationLogEntry(
            phase="discovery",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=result["summary"],
            metadata={
                "techniques": [t.value for t in result["categorization"].techniques],
                "confidence": result["categorization"].confidence
            }
        )
        
        return {
            "categorization": result["categorization"],
            "best_practices": result["best_practices"],
            "coordination_log": [log_entry]
        }
    
    async def _builder_node(self, state: WorkflowState) -> WorkflowState:
        """Builder agent node"""
        result = await self.builder.build_workflow(state)
        
        log_entry = CoordinationLogEntry(
            phase="builder",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=result["summary"],
            metadata={"nodes_added": result["nodes_added"]}
        )
        
        return {"coordination_log": [log_entry]}
    
    async def _configurator_node(self, state: WorkflowState) -> WorkflowState:
        """Configurator agent node"""
        result = await self.configurator.configure_workflow(state)
        
        log_entry = CoordinationLogEntry(
            phase="configurator",
            status="completed",
            timestamp=datetime.now().timestamp(),
            summary=result["summary"],
            metadata={"nodes_configured": result["nodes_configured"]}
        )
        
        return {"coordination_log": [log_entry]}
    
    async def _responder_node(self, state: WorkflowState) -> WorkflowState:
        """Responder agent node"""
        workflow = state["workflow_json"]
        
        response = f"""Workflow '{workflow.name}' has been built successfully!

Summary:
- {len(workflow.nodes)} nodes added
- {sum(len(conns) for conns in workflow.connections.values())} connections created

Workflow structure:
{self._format_workflow(workflow)}

The workflow is ready to execute!"""
        
        return {"messages": [{"role": "assistant", "content": response}]}
    
    def _format_workflow(self, workflow) -> str:
        """Format workflow for display"""
        lines = []
        
        for node in workflow.nodes:
            lines.append(f"• {node.name} ({node.type})")
            
            # Show connections
            if node.name in workflow.connections:
                for conn_type, conn_list in workflow.connections[node.name].items():
                    for conn_array in conn_list:
                        for conn in conn_array:
                            lines.append(f"  → {conn.node}")
        
        return "\n".join(lines)
    
    async def process_message(self, user_message: str, state: WorkflowState = None):
        """Process a user message and build workflow"""
        
        if state is None:
            state = create_initial_state()
        
        # Add user message
        state["messages"].append({"role": "user", "content": user_message})
        
        # Run graph
        result = await self.graph.ainvoke(state)
        
        return result

# # Example usage
# async def main():
#     # Load node types (in production, load from actual node definitions)
#     node_types = [
#         {
#             "name": "workflow.httpRequest",
#             "displayName": "HTTP Request",
#             "description": "Make HTTP requests to APIs",
#             "version": 1,
#             "inputs": ["main"],
#             "outputs": ["main"],
#             "properties": [
#                 {"name": "url", "type": "string", "required": True},
#                 {"name": "method", "type": "options", "options": ["GET", "POST", "PUT", "DELETE"]},
#             ]
#         },
#         {
#             "name": "workflow.scheduleTrigger",
#             "displayName": "Schedule Trigger",
#             "description": "Trigger workflow on a schedule",
#             "version": 1,
#             "inputs": [],
#             "outputs": ["main"],
#             "properties": [
#                 {"name": "rule", "type": "string"},
#             ]
#         },
#         {
#             "name": "workflow.set",
#             "displayName": "Set",
#             "description": "Set values",
#             "version": 1,
#             "inputs": ["main"],
#             "outputs": ["main"],
#             "properties": []
#         },
#         # Add more node types...
#     ]
#     print("Loaded node types:", len(node_types))
#     # Initialize orchestrator
#     orchestrator = WorkflowBuilderOrchestrator(
#         api_key="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",
#         node_types=node_types
#     )
#     print("Orchestrator initialized")
#     # Process user message
#     result = await orchestrator.process_message(
#         "Create a workflow that checks a weather API every hour and sends me an email if it's going to rain"
#     )
    
#     # Print result
#     print(json.dumps(result["workflow_json"].to_dict(), indent=2))
#     print("\nFinal message:", result["messages"][-1]["content"])

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())