# tools/validate_workflow.py
from langchain_core.tools import tool
from ..types.workflow import SimpleWorkflow

# Nodes whose VALUE means they are triggers
TRIGGER_VALUES = {"MANUAL", "SCHEDULE", "WEBHOOK"}
# Nodes whose VALUE means conditional
CONDITIONAL_VALUES = {"IF", "SWITCH", "FILTER"}


def create_validate_workflow_tool(workflow: SimpleWorkflow):

    @tool
    def validate_workflow() -> str:
        """
        Validate workflow completeness.
        Checks: has trigger, all nodes connected, logical flow.
        Call this once after connecting all nodes.
        """
        if not workflow.nodes:
            return "❌ Workflow has no nodes"

        issues = []

        # ── Check trigger ────────────────────────────────────────
        # node.type IS the value e.g. "SCHEDULE", "WEBHOOK", "MANUAL"
        trigger_found = any(
            node.type.upper() in TRIGGER_VALUES
            for node in workflow.nodes
        )
        if not trigger_found:
            issues.append(
                f"No trigger node found. Add one of: {', '.join(TRIGGER_VALUES)}"
            )

        # ── Check connectivity ────────────────────────────────────
        if len(workflow.nodes) > 1:
            connected_names = set()
            for source, conns in workflow.connections.items():
                connected_names.add(source)
                for _, arrays in conns.items():
                    for arr in arrays:
                        for c in arr:
                            connected_names.add(c.node)

            for node in workflow.nodes:
                if node.name not in connected_names:
                    issues.append(f"Node '{node.name}' ({node.type}) is not connected")

        if issues:
            return "⚠️  Validation warnings:\n- " + "\n- ".join(issues)

        node_summary = " → ".join(
            f"{n.name}({n.type})" for n in workflow.nodes
        )
        return f"✅ Validation passed! Flow: {node_summary}"

    return validate_workflow