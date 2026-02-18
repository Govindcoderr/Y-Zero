# tools/search_nodes.py
from langchain_core.tools import tool
from typing import List, Annotated
from backend.engines.node_search_engine import NodeSearchEngine

def create_search_nodes_tool(search_engine: NodeSearchEngine):
    @tool
    def search_nodes(
        query: Annotated[str, "Search query for node types"],
        limit: Annotated[int, "Maximum number of results"] = 10
    ) -> str:
        """Search for available workflow nodes by name or description.
        
        Use this before adding nodes to find the correct node types.
        """
        results = search_engine.search_by_name(query, limit)
        
        if not results:
            return f"No nodes found matching '{query}'"
        
        output = [f"Found {len(results)} nodes matching '{query}':\n"]
        
        for i, result in enumerate(results, 1):
            output.append(f"{i}. {result.display_name} ({result.name})")
            output.append(f"   Description: {result.description}")
            output.append(f"   Version: {result.version}")
            output.append("")
        
        return "\n".join(output)
    
    return search_nodes