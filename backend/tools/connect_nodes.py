# tools/connect_nodes.py
from langchain_core.tools import tool
from typing import Annotated
from ..types.workflow import WorkflowConnection
# from langgraph.prebuilt import InjectedState

def create_connect_nodes_tool():
    @tool
    def connect_nodes(
        state: dict,
        source_node_id: Annotated[str, "ID of the source node"],
        target_node_id: Annotated[str, "ID of the target node"],
        connection_type: Annotated[str, "Connection type"] = "main"
    ) -> str:
        """Connect two nodes in the workflow.
        
        Parameters:
        - source_node_id: UUID of the node that produces output
        - target_node_id: UUID of the node that receives input
        - connection_type: Type of connection (usually 'main')
        """
        workflow = state["workflow_json"]
        
        # Find nodes
        source_node = workflow.get_node_by_id(source_node_id)
        target_node = workflow.get_node_by_id(target_node_id)
        
        if not source_node:
            return f"Error: Source node {source_node_id} not found"
        if not target_node:
            return f"Error: Target node {target_node_id} not found"
        
        # Create connection
        if source_node.name not in workflow.connections:
            workflow.connections[source_node.name] = {}
        
        if connection_type not in workflow.connections[source_node.name]:
            workflow.connections[source_node.name][connection_type] = [[]]
        
        connection = WorkflowConnection(
            node=target_node.name,
            type=connection_type,
            index=0
        )
        
        workflow.connections[source_node.name][connection_type][0].append(connection)
        
        return f"Connected {source_node.name} → {target_node.name} ({connection_type})"
    
    return connect_nodes