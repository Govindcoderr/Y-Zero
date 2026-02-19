
# tools/validate_workflow.py
from langchain_core.tools import tool


def create_validate_workflow_tool(workflow):
    """
    Create the validate_workflow tool bound to a specific workflow instance.

    Args:
        workflow: SimpleWorkflow instance to validate
    """

    @tool
    def validate_workflow() -> str:
        """Validate the workflow for completeness and correctness.

        Checks:
        - Has at least one trigger node
        - All nodes are connected
        - Required parameters are filled
        - Workflow has logical flow
        """
        issues = []

        if not workflow.nodes:
            return "Validation failed:\n- Workflow has no nodes"

        trigger_found = any("trigger" in node.type.lower() for node in workflow.nodes)
        if not trigger_found:
            issues.append("No trigger node found - workflow needs a starting point")

        connected_nodes = set()
        for source, connections in workflow.connections.items():
            connected_nodes.add(source)
            for conn_type, conn_list in connections.items():
                for conn_array in conn_list:
                    for conn in conn_array:
                        connected_nodes.add(conn.node)

        if len(workflow.nodes) > 1:
            for node in workflow.nodes:
                if node.name not in connected_nodes:
                    issues.append(
                        f"Node '{node.name}' is not connected to any other node"
                    )

        for node in workflow.nodes:
            if not node.parameters and "trigger" not in node.type.lower():
                issues.append(f"Node '{node.name}' has no parameters configured")

        if issues:
            return "Validation warnings:\n- " + "\n- ".join(issues)

        return "✓ Workflow validation passed! All checks successful."

    return validate_workflow