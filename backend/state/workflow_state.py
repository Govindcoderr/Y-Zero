
# state/workflow_state.py
from typing import TypedDict, List, Dict, Any, Annotated, Optional
from langgraph.graph import add_messages
from ..types.categorization import PromptCategorization
from ..types.workflow import SimpleWorkflow
from ..types.coordination import CoordinationLogEntry
import operator


def merge_logs(left: List, right: List) -> List:
    """Append new log entries to existing ones."""
    return left + right


def merge_dicts(left: Dict, right: Dict) -> Dict:
    """Merge two dicts, right takes precedence."""
    return {**left, **right}


class WorkflowState(TypedDict):
    # Core workflow - stored as a dict to be serializable by LangGraph
    workflow_json: SimpleWorkflow

    # Categorization
    categorization: Optional[PromptCategorization]

    # Best practices
    best_practices: Optional[str]

    # Node configurations from examples
    node_configurations: Dict[str, List[Any]]

    # Messages - uses LangGraph reducer
    messages: Annotated[List[Any], add_messages]

    # Coordination log - uses append reducer
    coordination_log: Annotated[List[CoordinationLogEntry], merge_logs]

    # Available node types
    available_node_types: List[Dict[str, Any]]

    # Conversation history
    conversation_summary: Optional[str]

    # Next agent decision from supervisor
    next_agent: str


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
        "next_agent": "discovery",
    }