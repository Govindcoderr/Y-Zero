from langchain_core.tools import tool
from typing import Annotated


def create_remove_node_tool(workflow):
    @tool
    def remove_node(
        node_name: Annotated[str, "Exact node name to remove. You may also pass the node ID."],
        reconnect: Annotated[bool, "Reconnect upstream nodes to downstream nodes after removal."] = True,
    ) -> str:
        """Remove a node from the workflow and optionally reconnect the remaining graph."""
        node = workflow.get_node_by_name(node_name) or workflow.get_node_by_id(node_name)
        if not node:
            available = [n.name for n in workflow.nodes]
            return f"Node '{node_name}' not found. Available nodes: {available}"

        outgoing = workflow.connections.pop(node.name, {})
        outgoing_targets = []
        for connection_type, conn_arrays in outgoing.items():
            for branch_index, conn_array in enumerate(conn_arrays):
                outgoing_targets.append((connection_type, branch_index, list(conn_array)))

        incoming_refs = []
        for source_name, conn_types in list(workflow.connections.items()):
            for connection_type, conn_arrays in list(conn_types.items()):
                for branch_index, conn_array in enumerate(conn_arrays):
                    kept = []
                    removed_here = False
                    for conn in conn_array:
                        if conn.node == node.name:
                            removed_here = True
                        else:
                            kept.append(conn)
                    if removed_here:
                        incoming_refs.append(source_name)
                        workflow.connections[source_name][connection_type][branch_index] = kept

        workflow.nodes = [existing for existing in workflow.nodes if existing.id != node.id]

        if reconnect:
            for source_name in incoming_refs:
                for connection_type, branch_index, targets in outgoing_targets:
                    workflow.connections.setdefault(source_name, {})
                    workflow.connections[source_name].setdefault(connection_type, [])
                    while len(workflow.connections[source_name][connection_type]) <= branch_index:
                        workflow.connections[source_name][connection_type].append([])

                    existing_targets = {
                        conn.node for conn in workflow.connections[source_name][connection_type][branch_index]
                    }
                    for conn in targets:
                        if conn.node == source_name or conn.node in existing_targets:
                            continue
                        workflow.connections[source_name][connection_type][branch_index].append(conn)

        for source_name in list(workflow.connections.keys()):
            cleaned_types = {}
            for connection_type, conn_arrays in workflow.connections[source_name].items():
                if any(conn_arrays):
                    cleaned_types[connection_type] = conn_arrays
            if cleaned_types:
                workflow.connections[source_name] = cleaned_types
            else:
                workflow.connections.pop(source_name, None)

        return f"Removed node '{node.name}' ({node.type}). Reconnect applied: {reconnect}"

    return remove_node
