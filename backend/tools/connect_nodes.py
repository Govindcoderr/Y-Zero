

# # tools/connect_nodes.py
# from langchain_core.tools import tool
# from typing import Annotated
# from ..types.workflow import WorkflowConnection, SimpleWorkflow


# def create_connect_nodes_tool(workflow: SimpleWorkflow):
#     """
#     Create the connect_nodes tool bound to a specific workflow instance.
#     """

#     @tool
#     def connect_nodes(
#         source_node_id: Annotated[str, "ID of the source node"],
#         target_node_id: Annotated[str, "ID of the target node"],
#         connection_type: Annotated[str, "Connection type (usually 'main')"] = "main",
#     ) -> str:
#         """Connect two nodes in the workflow.

#         Parameters:
#         - source_node_id: UUID of the node that produces output
#         - target_node_id: UUID of the node that receives input
#         - connection_type: Type of connection (usually 'main')
#         """
#         source_node = workflow.get_node_by_id(source_node_id)
#         target_node = workflow.get_node_by_id(target_node_id)

#         if not source_node:
#             # Try finding by name as fallback
#             source_node = workflow.get_node_by_name(source_node_id)
#         if not target_node:
#             target_node = workflow.get_node_by_name(target_node_id)

#         if not source_node:
#             return f"Error: Source node '{source_node_id}' not found"
#         if not target_node:
#             return f"Error: Target node '{target_node_id}' not found"

#         if source_node.name not in workflow.connections:
#             workflow.connections[source_node.name] = {}

#         if connection_type not in workflow.connections[source_node.name]:
#             workflow.connections[source_node.name][connection_type] = [[]]

#         connection = WorkflowConnection(
#             node=target_node.name,
#             type=connection_type,
#             index=0,
#         )

#         workflow.connections[source_node.name][connection_type][0].append(connection)

#         return f"Connected '{source_node.name}' → '{target_node.name}' ({connection_type})"

#     return connect_nodes

# tools/connect_nodes.py
from langchain_core.tools import tool
from typing import Annotated
from ..types.workflow import WorkflowConnection


def create_connect_nodes_tool(workflow):
    """
    Create connection tools bound to a specific workflow instance.
    Returns TWO tools: connect by ID and connect by name.
    """

    @tool
    def connect_nodes_by_name(
        source_node_name: Annotated[str, "Exact name of the source node (the one sending data)"],
        target_node_name: Annotated[str, "Exact name of the target node (the one receiving data)"],
        connection_type: Annotated[str, "Connection type, almost always 'main'"] = "main",
    ) -> str:
        """Connect two nodes by their names. Use this after add_node to link nodes together.

        IMPORTANT: Call this for every consecutive pair of nodes to build the workflow chain.
        Example: if you added NodeA, NodeB, NodeC - call this twice:
          connect_nodes_by_name("NodeA", "NodeB")
          connect_nodes_by_name("NodeB", "NodeC")
        """
        source_node = workflow.get_node_by_name(source_node_name)
        target_node = workflow.get_node_by_name(target_node_name)

        if not source_node:
            available = [n.name for n in workflow.nodes]
            return f"Error: Source node '{source_node_name}' not found. Available nodes: {available}"
        if not target_node:
            available = [n.name for n in workflow.nodes]
            return f"Error: Target node '{target_node_name}' not found. Available nodes: {available}"

        if source_node.name not in workflow.connections:
            workflow.connections[source_node.name] = {}

        if connection_type not in workflow.connections[source_node.name]:
            workflow.connections[source_node.name][connection_type] = [[]]

        connection = WorkflowConnection(
            node=target_node.name,
            type=connection_type,
            index=0,
        )
        workflow.connections[source_node.name][connection_type][0].append(connection)

        return f"✓ Connected '{source_node.name}' → '{target_node.name}' ({connection_type})"

    @tool
    def connect_nodes_by_id(
        source_node_id: Annotated[str, "UUID of the source node (from add_node response)"],
        target_node_id: Annotated[str, "UUID of the target node (from add_node response)"],
        connection_type: Annotated[str, "Connection type, almost always 'main'"] = "main",
    ) -> str:
        """Connect two nodes by their UUIDs returned from add_node."""
        source_node = workflow.get_node_by_id(source_node_id)
        target_node = workflow.get_node_by_id(target_node_id)

        if not source_node:
            source_node = workflow.get_node_by_name(source_node_id)
        if not target_node:
            target_node = workflow.get_node_by_name(target_node_id)

        if not source_node:
            available = [n.name for n in workflow.nodes]
            return f"Error: Source node '{source_node_id}' not found. Available nodes: {available}"
        if not target_node:
            available = [n.name for n in workflow.nodes]
            return f"Error: Target node '{target_node_id}' not found. Available nodes: {available}"

        if source_node.name not in workflow.connections:
            workflow.connections[source_node.name] = {}

        if connection_type not in workflow.connections[source_node.name]:
            workflow.connections[source_node.name][connection_type] = [[]]

        connection = WorkflowConnection(
            node=target_node.name,
            type=connection_type,
            index=0,
        )
        workflow.connections[source_node.name][connection_type][0].append(connection)

        return f"✓ Connected '{source_node.name}' → '{target_node.name}' ({connection_type})"

    return connect_nodes_by_name, connect_nodes_by_id