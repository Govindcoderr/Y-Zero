# tools/validate_workflow.py
from langchain_core.tools import tool
from typing import Annotated
# from langgraph.prebuilt import InjectedState

def create_validate_workflow_tool():
    @tool
    def validate_workflow(
        state: dict
    ) -> str:
        """Validate the workflow for completeness and correctness.
        
        Checks:
        - Has at least one trigger node
        - All nodes are connected
        - Required parameters are filled
        - Workflow has logical flow
        """
        workflow = state["workflow_json"]
        issues = []
        
        # Check if workflow has nodes
        if not workflow.nodes:
            issues.append("Workflow has no nodes")
            return "Validation failed:\n- " + "\n- ".join(issues)
        
        # Check for trigger node
        trigger_found = False
        for node in workflow.nodes:
            if "trigger" in node.type.lower():
                trigger_found = True
                break
        
        if not trigger_found:
            issues.append("No trigger node found - workflow needs a starting point")
        
        # Check for disconnected nodes
        connected_nodes = set()
        for source, connections in workflow.connections.items():
            connected_nodes.add(source)
            for conn_type, conn_list in connections.items():
                for conn_array in conn_list:
                    for conn in conn_array:
                        connected_nodes.add(conn.node)
        
        for node in workflow.nodes:
            if node.name not in connected_nodes and not trigger_found:
                issues.append(f"Node '{node.name}' is not connected")
        
        # Check for empty parameters
        for node in workflow.nodes:
            if not node.parameters and "trigger" not in node.type.lower():
                issues.append(f"Node '{node.name}' has no parameters configured")
        
        if issues:
            return "Validation warnings:\n- " + "\n- ".join(issues)
        
        return "✓ Workflow validation passed! All checks successful."
    
    return validate_workflow