
# # backend/tools/validate_workflow.py
# from langchain_core.tools import tool
# from ..types.workflow import SimpleWorkflow, _NODE_REGISTRY


# def create_validate_workflow_tool(workflow: SimpleWorkflow):

#     @tool
#     def validate_workflow() -> str:
#         """
#         Validate workflow completeness.
#         Checks: has trigger, all nodes connected, logical flow.
#         Call once after connecting all nodes.
#         """
#         if not workflow.nodes:
#             return "❌ Workflow has no nodes"

#         issues = []

#         # ── Dynamic trigger check — registry se ──────────────────
#         def is_trigger(node_type: str) -> bool:
#             node_data = _NODE_REGISTRY.get(node_type, {})
#             nt = node_data.get("nodeType", "").lower()
#             if nt == "trigger":
#                 return True
#             if node_data.get("triggers"):
#                 return True
#             return False

#         trigger_found = any(is_trigger(n.type) for n in workflow.nodes)
#         if not trigger_found:
#             trigger_nodes = [
#                 name for name, data in _NODE_REGISTRY.items()
#                 if data.get("nodeType", "").lower() == "trigger" or data.get("triggers")
#             ]
#             issues.append(
#                 f"No trigger node found. Available triggers: {', '.join(trigger_nodes[:5])}"
#             )

#         # ── Connectivity check ────────────────────────────────────
#         if len(workflow.nodes) > 1:
#             connected_names = set()
#             for source, conns in workflow.connections.items():
#                 connected_names.add(source)
#                 for _, arrays in conns.items():
#                     for arr in arrays:
#                         for c in arr:
#                             connected_names.add(c.node)

#             for node in workflow.nodes:
#                 if node.name not in connected_names:
#                     issues.append(f"Node '{node.name}' ({node.type}) is not connected")

#         if issues:
#             return "⚠️  Validation warnings:\n- " + "\n- ".join(issues)

#         node_summary = " → ".join(f"{n.name}({n.type})" for n in workflow.nodes)
#         return f"-->> Validation passed! Flow: {node_summary}"

#     return validate_workflow 



# backend/tools/validate_workflow.py
from langchain_core.tools import tool
from ..types.workflow import SimpleWorkflow, WorkflowNode, WorkflowConnection, _NODE_REGISTRY
import uuid


# Default trigger to auto-insert when none found
_DEFAULT_TRIGGER_TYPE = "MANUAL"
_DEFAULT_TRIGGER_NAME = "Start Workflow"


_TRIGGER_KEYWORDS = {
    "TRIGGER", "MANUAL", "SCHEDULE", "WEBHOOK", "CRON", "POLL",
    "SCHEDULER", "TIMER", "LISTEN", "WATCH",
}

def _is_trigger(node) -> bool:
    """
    Check if a WorkflowNode is a trigger.

    Priority:
      1. Registry nodeType field == 'trigger'
      2. Registry triggers array non-empty
      3. Keyword match in node.type string
    """
       # Priority 1: explicit role
    if node.role == "trigger":
        return True
    if node.role in ("action", "conditional"):
        return False
    node_type = getattr(node, "type", "")

    # 1 & 2 — registry lookup (most reliable)
    node_data = _NODE_REGISTRY.get(node_type, {})
    if node_data.get("nodeType", "").lower() == "trigger":
        return True
    if node_data.get("triggers"):
        return True

    # 3 — keyword fallback (handles MANUAL, SCHEDULE TRIGGER, WEBHOOK etc.)
    upper = node_type.upper()
    return any(kw in upper for kw in _TRIGGER_KEYWORDS)


def _auto_insert_trigger(workflow: SimpleWorkflow) -> str:
    """
    Auto-insert a MANUAL trigger at position 0 and connect it to first node.
    Returns a message describing what was done.
    """
    trigger_type = _DEFAULT_TRIGGER_TYPE
    trigger_name = _DEFAULT_TRIGGER_NAME

    # Check if MANUAL exists in registry, else use first available trigger
    if trigger_type not in _NODE_REGISTRY:
        available_triggers = [
            name for name, data in _NODE_REGISTRY.items()
            if data.get("nodeType", "").lower() == "trigger" or data.get("triggers")
        ]
        if available_triggers:
            trigger_type = available_triggers[0]
            trigger_name = f"Start Workflow ({trigger_type})"

    # Create trigger node
    trigger_node = WorkflowNode(
        id=str(uuid.uuid4()),
        name=trigger_name,
        type=trigger_type,
        type_version=1,
        position=(100, 300),
        parameters={"operation": "1"},
        role="trigger",
    )

    # Insert at position 0
    workflow.nodes.insert(0, trigger_node)

    # Connect trigger → old first node
    if len(workflow.nodes) > 1:
        second_node = workflow.nodes[1]  # old first node
        workflow.connections.setdefault(trigger_name, {}).setdefault("main", [[]])
        workflow.connections[trigger_name]["main"][0].append(
            WorkflowConnection(node=second_node.name, type="main", index=0)
        )
        return (
            f"⚡ Auto-fixed: Added '{trigger_name}' ({trigger_type}) as trigger\n"
            f"   Connected: '{trigger_name}' → '{second_node.name}'"
        )

    return f"⚡ Auto-fixed: Added '{trigger_name}' ({trigger_type}) as trigger"


def create_validate_workflow_tool(workflow: SimpleWorkflow):

    @tool
    def validate_workflow() -> str:
        """
        Validate workflow completeness AND auto-fix issues.

        Checks:
          1. Workflow not empty
          2. Trigger node present (auto-inserts MANUAL if missing)
          3. All nodes connected

        Call once after adding and connecting all nodes.
        Auto-fix will insert a trigger if missing — no need to retry.
        """
        # ── Check 1: Empty ────────────────────────────────────────
        if not workflow.nodes:
            return "❌ Workflow is empty — add nodes first"

        fixes_applied = []

        # ── Check 2: Trigger missing → AUTO FIX ──────────────────
        trigger_nodes = [n for n in workflow.nodes if _is_trigger(n)]

        if not trigger_nodes:
            fix_msg = _auto_insert_trigger(workflow)
            fixes_applied.append(fix_msg)

        # ── Check 3: Connectivity ─────────────────────────────────
        issues = []

        if len(workflow.nodes) > 1:
            connected_names = set()
            for source, conns in workflow.connections.items():
                connected_names.add(source)
                for _, arrays in conns.items():
                    for arr in arrays:
                        for c in arr:
                            connected_names.add(c.node)

            disconnected = [
                n.name for n in workflow.nodes
                if n.name not in connected_names
            ]

            # Auto-connect disconnected nodes in sequence
            for node_name in disconnected:
                node_idx = next(
                    (i for i, n in enumerate(workflow.nodes) if n.name == node_name), -1
                )
                if node_idx > 0:
                    prev_node = workflow.nodes[node_idx - 1]
                    workflow.connections.setdefault(prev_node.name, {}).setdefault("main", [[]])
                    workflow.connections[prev_node.name]["main"][0].append(
                        WorkflowConnection(node=node_name, type="main", index=0)
                    )
                    fixes_applied.append(
                        f"⚡ Auto-connected: '{prev_node.name}' → '{node_name}'"
                    )

        # ── Build result ──────────────────────────────────────────
        node_summary = " → ".join(
            f"{n.name}({n.type})" for n in workflow.nodes
        )

        if fixes_applied:
            fixes_text = "\n".join(fixes_applied)
            return (
                f"-->> Validation passed! (with auto-fixes)\n\n"
                f"Auto-fixes applied:\n{fixes_text}\n\n"
                f"Final flow: {node_summary}"
            )

        return f"-->> Validation passed!\nFlow: {node_summary}"

    return validate_workflow