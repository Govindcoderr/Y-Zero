# state/workflow_state.py
from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import add_messages
from ..types.categorization import PromptCategorization
from ..types.workflow import SimpleWorkflow
from ..types.coordination import CoordinationLogEntry

class WorkflowState(TypedDict):
    # Core workflow
    workflow_json: SimpleWorkflow
    
    # Categorization
    categorization: PromptCategorization | None
    
    # Best practices
    best_practices: str | None
    
    # Node configurations from examples
    node_configurations: Dict[str, List[Any]]
    
    # Messages
    messages: Annotated[List[Any], add_messages]
    
    # Coordination log
    coordination_log: List[CoordinationLogEntry]
    
    # Available node types
    available_node_types: List[Dict[str, Any]]
    
    # Conversation history
    conversation_summary: str | None

def create_initial_state() -> WorkflowState:
    return {
        "workflow_json": SimpleWorkflow(name="New Workflow"),
        "categorization": None,
        "best_practices": None,
        "node_configurations": {},
        "messages": [],
        "coordination_log": [],
        "available_node_types": [],
        "conversation_summary": None,
    }