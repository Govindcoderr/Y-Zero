

# agents/supervisor.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any


class SupervisorDecision(BaseModel):
    next_agent: Literal["discovery", "builder", "configurator", "responder"] = Field(
        description="Which agent should act next"
    )
    reasoning: str = Field(description="Why this agent should act", default="")


class SupervisorAgent:
    """Agent that orchestrates the workflow building process"""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def decide_next_agent(self, state: Dict[str, Any]) -> str:
        """Decide which agent should act next based on current state"""

        workflow = state["workflow_json"]
        has_categorization = state.get("categorization") is not None
        has_best_practices = state.get("best_practices") is not None
        node_count = len(workflow.nodes)

        completed_phases = set()
        for entry in state.get("coordination_log", []):
            if entry.status == "completed":
                completed_phases.add(entry.phase)

        # Hard-coded routing logic to avoid LLM call overhead and avoid loops
        if not has_categorization or not has_best_practices:
            return "discovery"

        if "builder" not in completed_phases:
            return "builder"

        if "configurator" not in completed_phases:
            return "configurator"

        return "responder"