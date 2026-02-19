# tools/update_parameters.py
from langchain_core.tools import tool
from typing import Annotated, List
# from langgraph.prebuilt import InjectedState
from backend.chains.parameter_updater import update_node_parameters
from langchain_core.language_models import BaseChatModel

from backend.types.workflow import SimpleWorkflow

def create_update_parameters_tool(llm: BaseChatModel, search_engine, workflow: SimpleWorkflow):
    @tool
    async def update_node_parameters_tool(
        state: dict,
        node_id: Annotated[str, "ID of the node to update"],
        changes: Annotated[List[str], "List of changes to apply"]
    ) -> str:
        """Update node parameters based on natural language descriptions.
        
        Parameters:
        - node_id: UUID of the node
        - changes: List of changes like ["Set URL to https://api.example.com", "Add authorization header"]
        """
        workflow = state["workflow_json"]
        
        # Find node
        node = workflow.get_node_by_id(node_id)
        if not node:
            return f"Error: Node {node_id} not found"
        
        # Get node details
        node_details = search_engine.get_node_details(node.type, node.type_version)
        if not node_details:
            return f"Error: Node type {node.type} not found"
        
        # Update parameters using LLM
        updated_params = await update_node_parameters(
            llm=llm,
            node_type=node.type,
            current_parameters=node.parameters,
            node_properties=node_details.properties,
            changes=changes
        )
        
        node.parameters = updated_params
        
        changes_text = "\n".join(f"  - {change}" for change in changes)
        return f"Updated parameters for {node.name}:\n{changes_text}"
    
    return update_node_parameters_tool