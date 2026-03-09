# # tools/update_parameters.py old way 
# from langchain_core.tools import tool
# from typing import Annotated, List
# # from langgraph.prebuilt import InjectedState
# from backend.chains.parameter_updater import update_node_parameters
# from langchain_core.language_models import BaseChatModel

# from backend.types.workflow import SimpleWorkflow

# def create_update_parameters_tool(llm: BaseChatModel, search_engine, workflow: SimpleWorkflow):
#     @tool
#     async def update_node_parameters_tool(
#         state: dict,
#         node_id: Annotated[str, "ID of the node to update"],
#         changes: Annotated[List[str], "List of changes to apply"]
#     ) -> str:
#         """Update node parameters based on natural language descriptions.
        
#         Parameters:
#         - node_id: UUID of the node
#         - changes: List of changes like ["Set URL to https://api.example.com", "Add authorization header"]
#         """
#         workflow = state["workflow_json"]
        
#         # Find node
#         node = workflow.get_node_by_id(node_id)
#         if not node:
#             return f"Error: Node {node_id} not found"
        
#         # Get node details
#         node_details = search_engine.get_node_details(node.type, node.type_version)
#         if not node_details:
#             return f"Error: Node type {node.type} not found"
        
#         # Update parameters using LLM
#         updated_params = await update_node_parameters(
#             llm=llm,
#             node_type=node.type,
#             current_parameters=node.parameters,
#             node_properties=node_details.properties,
#             changes=changes
#         )
        
#         node.parameters = updated_params
        
#         changes_text = "\n".join(f"  - {change}" for change in changes)
#         return f"Updated parameters for {node.name}:\n{changes_text}"
    
#     return update_node_parameters_tool


# backend/tools/update_parameters.py
"""
update_parameters tool — node parameters ko directly update karta hai.
LLM is tool ko call karta hai jab kisi node ke parameters change karne hon.
"""

from langchain_core.tools import tool
from typing import Annotated, Dict, Any
from ..types.workflow import SimpleWorkflow


def create_update_parameters_tool(workflow: SimpleWorkflow):

    @tool
    def update_parameters(
        node_name: Annotated[str, "Exact name of the node to update (as given to add_node)"],
        parameters: Annotated[Dict[str, Any], "Complete parameters dict to set on the node — merges with existing"],
    ) -> str:
        """
        Update parameters of an existing node in the workflow.

        Use this to set or change node-specific values like:
        - URLs, API keys, resource, operation
        - chatId, message, subject, body
        - schedule expressions, conditions, etc.

        IMPORTANT: Use the exact node name that was used in add_node.
        Parameters are MERGED with existing — you only need to pass what changes.

        Example:
          update_parameters("Send Telegram Message", {"chatId": "123456", "message": "Hello!"})
          update_parameters("Schedule Trigger", {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}})
        """
        # Find node by name
        node = workflow.get_node_by_name(node_name)

        if not node:
            available = [n.name for n in workflow.nodes]
            return (
                f"❌ Node '{node_name}' not found.\n"
                f"   Available nodes: {available}"
            )

        # Merge — new values override existing
        before = dict(node.parameters)
        node.parameters.update(parameters)

        changed_keys = list(parameters.keys())
        return (
            f"✅ Updated '{node_name}' ({node.type})\n"
            f"   Changed keys: {changed_keys}\n"
            f"   Parameters now: {node.parameters}"
        )

    return update_parameters