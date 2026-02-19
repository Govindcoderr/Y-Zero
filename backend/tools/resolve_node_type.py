# tools/resolve_node_type.py
from langchain_core.tools import tool
from typing import Annotated


def create_resolve_node_type_tool(search_engine):
    """
    Tool that validates a node type name against the JSON file and
    returns the best available alternative if it's not found.
    """

    @tool
    def resolve_node_type(
        requested_node_type: Annotated[
            str,
            "The node type you want to use (e.g. 'workflow.whatsapp', 'workflow.telegram')"
        ],
    ) -> str:
        """Check if a node type exists in the available node list.

        ALWAYS call this before add_node to confirm the node type is valid.
        If the requested type doesn't exist, this returns the best available
        alternative with an explanation of why.

        Returns: the exact node_type string you should pass to add_node.
        """
        actual, explanation = search_engine.resolve_node_type(requested_node_type)
        available_nodes = search_engine.get_all_node_names()
        node_list = "\n".join(
            f"  - {n['name']} ({n['displayName']}): {n['description']}"
            for n in available_nodes
        )
        return (
            f"RESOLVED: use node_type = '{actual}'\n"
            f"REASON: {explanation}\n\n"
            f"All available node types:\n{node_list}"
        )

    return resolve_node_type