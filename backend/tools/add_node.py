

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



# # tools/add_node.py
# from langchain_core.tools import tool
# from typing import Annotated, Dict, Any, Optional
# from ..types.workflow import WorkflowNode, SimpleWorkflow
# import uuid


# def create_add_node_tool(workflow: SimpleWorkflow, search_engine=None):
#     """
#     Create the add_node tool bound to a specific workflow instance.

#     Args:
#         workflow: SimpleWorkflow instance to mutate in-place
#         search_engine: NodeSearchEngine used to auto-resolve unknown node types
#     """

#     @tool
#     def add_node(
#         node_type: Annotated[
#             str,
#             "The node type name. Must be from the available node list. "
#             "Call resolve_node_type first if unsure."
#         ],
#         name: Annotated[str, "Descriptive human-readable name for this node"],
#         parameters: Annotated[
#             Optional[Dict[str, Any]],
#             "Initial node parameters as a dict"
#         ] = None,
#     ) -> str:
#         """Add a new node to the workflow.

#         IMPORTANT: Only use node_type values that exist in the available node list.
#         If unsure, call resolve_node_type first to get the correct type.

#         Returns the node's UUID — save it if you want to use connect_nodes_by_id.
#         """
#         # Auto-resolve the node type if search_engine is available
#         resolved_type = node_type
#         resolution_note = ""
#         if search_engine is not None:
#             actual, explanation = search_engine.resolve_node_type(node_type)
#             if actual != node_type:
#                 resolution_note = f" [auto-resolved from '{node_type}': {explanation}]"
#             resolved_type = actual

#         node_id = str(uuid.uuid4())
#         x_pos = 250 + len(workflow.nodes) * 280
#         y_pos = 300

#         new_node = WorkflowNode(
#             id=node_id,
#             name=name,
#             type=resolved_type,
#             type_version=1,
#             position=(x_pos, y_pos),
#             parameters=parameters or {},
#         )

#         workflow.add_node(new_node)

#         return (
#             f"Successfully added node '{name}' "
#             f"(type={resolved_type}) "
#             f"with ID {node_id}"
#             f"{resolution_note}"
#         )

#     return add_node




# # tools/add_node.py
# from langchain_core.tools import tool
# from typing import Annotated, Dict, Any
# from ..types.workflow import WorkflowNode, SimpleWorkflow
# from ..engines.node_search_engine import NodeSearchEngine
# import uuid


# def create_add_node_tool(workflow: SimpleWorkflow, search_engine: NodeSearchEngine):

#     @tool
#     def add_node(
#         node_type: Annotated[str, "The node VALUE name from search results e.g. 'HTTP REQUEST', 'TELEGRAM', 'IF'"],
#         name:      Annotated[str, "Descriptive label for this node e.g. 'Fetch Weather Data'"],
#         role:       Annotated[str, "Node ka role: 'trigger' | 'action' | 'conditional'"], 
#         parameters: Annotated[Dict[str, Any], "Node parameters as key-value pairs"] = None,
#     ) -> str:
#         """
#         Add a node to the workflow.

#         IMPORTANT:
#         - node_type must be an EXACT value from search_nodes results (e.g. 'HTTP REQUEST', 'TELEGRAM')
#         - name is a human-readable label describing what THIS node does
#         - Always call search_nodes first to confirm the correct node_type

#         Node type categories:
#           Triggers:     MANUAL, SCHEDULE, WEBHOOK
#           Actions:      HTTP REQUEST, TELEGRAM, SLACK, WHATSAPP, SEND EMAIL, OPENAI, ...
#           Conditionals: IF, SWITCH, FILTER

#         Branching guide:
#         - Use IF only for one simple boolean split: true/false, yes/no, pass/fail.
#         - Use SWITCH for 3 or more branches.
#         - Use SWITCH also for 2 branches when both branches are explicit separate conditions
#           such as approved/rejected, high/low, email/sms, status/value based routing.
#         """
#         # Auto-resolve if LLM passes something other than exact name
#         resolved_type, reason = search_engine.resolve_node_type(node_type)

#         node_id = str(uuid.uuid4())
#         x_pos   = 250 + len(workflow.nodes) * 280
#         y_pos   = 300

#         # Merge provided parameters with node defaults from search engine
#         node_defaults = {}
#         details = search_engine.get_node_details(resolved_type)
#         if details and details.properties:
#             # properties in node_types.json are the default parameter dict (not a list here)
#             pass

#         new_node = WorkflowNode(
#             id=node_id,
#             name=name,
#             type=resolved_type,
#             type_version=1,
#             position=(x_pos, y_pos),
#             parameters=parameters or {},
#             role=role,   # ← ADD THIS
#         )

#         workflow.add_node(new_node)

#         note = ""
#         if resolved_type != node_type:
#             note = f" (auto-resolved from '{node_type}' via {reason})"

#         return (
#             f"✅ Added node '{name}'"
#             f"\n   type  = {resolved_type}{note}"
#             f"\n   id    = {node_id}"
#             f"\n   total nodes = {len(workflow.nodes)}"
#         )

#     return add_node



# backend/tools/add_node.py
#
# CHANGE: `role` parameter LLM se nahi liya jata.
# Role ab poori tarah _NODE_REGISTRY se infer hota hai via _infer_output_type().
# LLM sirf node_type, name, aur parameters deta hai — role ka koi control nahi.

from langchain_core.tools import tool
from typing import Annotated, Dict, Any
from ..types.workflow import WorkflowNode, SimpleWorkflow, _infer_output_type
from ..engines.node_search_engine import NodeSearchEngine
import uuid


def create_add_node_tool(workflow: SimpleWorkflow, search_engine: NodeSearchEngine):

    @tool
    def add_node(
        node_type: Annotated[
            str,
            "The node VALUE name from search results e.g. 'HTTP REQUEST', 'TELEGRAM', 'IF'"
        ],
        name: Annotated[
            str,
            "Descriptive label for this node e.g. 'Fetch Weather Data'"
        ],
        parameters: Annotated[
            Dict[str, Any],
            "Node parameters as key-value pairs"
        ] = None,
    ) -> str:
        """
        Add a node to the workflow.

        IMPORTANT:
        - node_type must be an EXACT value from search_nodes results
          (e.g. 'HTTP REQUEST', 'TELEGRAM', 'SCHEDULE TRIGGER')
        - name is a human-readable label describing what THIS node does
        - Always call search_nodes first to confirm the correct node_type
        - Do NOT pass a 'role' — it is determined automatically from the node catalog

        Node type categories (auto-detected from catalog):
          Triggers:     MANUAL, SCHEDULE TRIGGER, WEBHOOK, TYPEFORM, ...
          Actions:      HTTP REQUEST, TELEGRAM, SLACK, GMAIL, OPENAI, ...
          Conditionals: IF, SWITCH, FILTER
        """
        # 1. Resolve node_type against registry (fuzzy fallback if needed)
        resolved_type, reason = search_engine.resolve_node_type(node_type)

        # 2. Infer role from registry — LLM has zero input here
        inferred_role = _infer_output_type(resolved_type)

        # 3. Build and append node
        node_id = str(uuid.uuid4())
        x_pos   = 250 + len(workflow.nodes) * 280
        y_pos   = 300

        new_node = WorkflowNode(
            id=node_id,
            name=name,
            type=resolved_type,
            type_version=1,
            position=(x_pos, y_pos),
            parameters=parameters or {},
            role=inferred_role,   # ← registry-driven, not LLM-driven
        )

        workflow.add_node(new_node)

        note = ""
        if resolved_type != node_type:
            note = f"\n   resolved from '{node_type}' via {reason}"

        return (      
            f"-->> Added node '{name}'"
            f"\n   type  = {resolved_type}{note}"
            f"\n   role  = {inferred_role}  (auto-detected from catalog)"
            f"\n   id    = {node_id}"
            f"\n   total nodes = {len(workflow.nodes)}"
        )

    return add_node