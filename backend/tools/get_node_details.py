# tools/get_node_details.py
from langchain_core.tools import tool
from typing import Annotated
from backend.tools.search_nodes import NodeSearchEngine
import json

def create_get_node_details_tool(search_engine: NodeSearchEngine):
    @tool
    def get_node_details(
        node_name: Annotated[str, "The exact node type name (e.g., 'workflow.httpRequest')"],
        version: Annotated[int, "The node version"] = 1
    ) -> str:
        """Get detailed information about a specific node type.
        
        Use this before adding a node to understand its parameters and capabilities.
        """
        details = search_engine.get_node_details(node_name, version)
        
        if not details:
            return f"Node '{node_name}' version {version} not found"
        
        output = [
            f"Node Details: {details.display_name}",
            f"Name: {details.name}",
            f"Version: {details.version}",
            f"Description: {details.description}",
            "",
            "Inputs:",
            json.dumps(details.inputs, indent=2),
            "",
            "Outputs:",
            json.dumps(details.outputs, indent=2),
            "",
            f"Properties: {len(details.properties)} available"
        ]
        
        return "\n".join(output)
    
    return get_node_details