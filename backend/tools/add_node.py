# tools/add_node.py
from langchain_core.tools import tool
from typing import Annotated, Dict, Any
from ..types.workflow import WorkflowNode
# from langgraph.prebuilt import InjectedState
import uuid

def create_add_node_tool():
    @tool
    def add_node(
        state: dict,
        node_type: Annotated[str, "The node type name"],
        name: Annotated[str, "Descriptive name for the node"],
        parameters: Annotated[Dict[str, Any], "Node parameters"] = None
    ) -> str:
        """Add a new node to the workflow.
        
        Parameters:
        - node_type: Full node type name (e.g., 'workflow.httpRequest')
        - name: Descriptive name that explains what the node does
        - parameters: Optional initial parameters
        """
        workflow = state["workflow_json"]
        
        # Generate unique ID
        node_id = str(uuid.uuid4())
        
        # Calculate position
        x_pos = 250 + len(workflow.nodes) * 280
        y_pos = 300
        
        # Create node
        new_node = WorkflowNode(
            id=node_id,
            name=name,
            type=node_type,
            type_version=1,
            position=(x_pos, y_pos),
            parameters=parameters or {}
        )
        
        workflow.add_node(new_node)
        
        return f"Successfully added node '{name}' ({node_type}) with ID {node_id}"
    
    return add_node