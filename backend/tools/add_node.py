

# # tools/add_node.py
# # NOTE: LangGraph tools cannot directly mutate state.
# # The builder agent calls these tools and applies results back to state.
# # We pass the workflow object directly via closure.
# from langchain_core.tools import tool
# from typing import Annotated, Dict, Any, Optional
# from ..types.workflow import WorkflowNode, SimpleWorkflow
# import uuid


# def create_add_node_tool(workflow: SimpleWorkflow):
#     """
#     Create the add_node tool bound to a specific workflow instance.
#     The workflow object is mutated in place so state always reflects changes.
#     """

#     @tool
#     def add_node(
#         node_type: Annotated[str, "The node type name (e.g. 'workflow.httpRequest')"],
#         name: Annotated[str, "Descriptive name for the node"],
#         parameters: Annotated[Optional[Dict[str, Any]], "Node parameters"] = None,
#     ) -> str:
#         """Add a new node to the workflow.

#         Parameters:
#         - node_type: Full node type name (e.g., 'workflow.httpRequest')
#         - name: Descriptive name that explains what the node does
#         - parameters: Optional initial parameters
#         """
#         node_id = str(uuid.uuid4())

#         x_pos = 250 + len(workflow.nodes) * 280
#         y_pos = 300

#         new_node = WorkflowNode(
#             id=node_id,
#             name=name,
#             type=node_type,
#             type_version=1,
#             position=(x_pos, y_pos),
#             parameters=parameters or {},
#         )

#         workflow.add_node(new_node)

#         return f"Successfully added node '{name}' ({node_type}) with ID {node_id}"

#     return add_node



# tools/add_node.py
from langchain_core.tools import tool
from typing import Annotated, Dict, Any, Optional
from ..types.workflow import WorkflowNode, SimpleWorkflow
import uuid


def create_add_node_tool(workflow: SimpleWorkflow, search_engine=None):
    """
    Create the add_node tool bound to a specific workflow instance.

    Args:
        workflow: SimpleWorkflow instance to mutate in-place
        search_engine: NodeSearchEngine used to auto-resolve unknown node types
    """

    @tool
    def add_node(
        node_type: Annotated[
            str,
            "The node type name. Must be from the available node list. "
            "Call resolve_node_type first if unsure."
        ],
        name: Annotated[str, "Descriptive human-readable name for this node"],
        parameters: Annotated[
            Optional[Dict[str, Any]],
            "Initial node parameters as a dict"
        ] = None,
    ) -> str:
        """Add a new node to the workflow.

        IMPORTANT: Only use node_type values that exist in the available node list.
        If unsure, call resolve_node_type first to get the correct type.

        Returns the node's UUID — save it if you want to use connect_nodes_by_id.
        """
        # Auto-resolve the node type if search_engine is available
        resolved_type = node_type
        resolution_note = ""
        if search_engine is not None:
            actual, explanation = search_engine.resolve_node_type(node_type)
            if actual != node_type:
                resolution_note = f" [auto-resolved from '{node_type}': {explanation}]"
            resolved_type = actual

        node_id = str(uuid.uuid4())
        x_pos = 250 + len(workflow.nodes) * 280
        y_pos = 300

        new_node = WorkflowNode(
            id=node_id,
            name=name,
            type=resolved_type,
            type_version=1,
            position=(x_pos, y_pos),
            parameters=parameters or {},
        )

        workflow.add_node(new_node)

        return (
            f"Successfully added node '{name}' "
            f"(type={resolved_type}) "
            f"with ID {node_id}"
            f"{resolution_note}"
        )

    return add_node