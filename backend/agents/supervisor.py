# agents/supervisor.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field
from typing import Literal , Dict, Any

class SupervisorDecision(BaseModel):
    next_agent: Literal["discovery", "builder", "configurator", "responder"] = Field(
        description="Which agent should act next"
    )
    reasoning: str = Field(description="Why this agent should act")

class SupervisorAgent:
    """Agent that orchestrates the workflow building process"""
    
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
    
    async def decide_next_agent(self, state: Dict[str, Any]) -> str:
        """Decide which agent should act next"""
        
        workflow = state["workflow_json"]
        has_categorization = state.get("categorization") is not None
        has_best_practices = state.get("best_practices") is not None
        node_count = len(workflow.nodes)
        
        # Check coordination log
        completed_phases = set()
        for entry in state.get("coordination_log", []):
            if entry.status == "completed":
                completed_phases.add(entry.phase)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a workflow orchestration supervisor. 
            Analyze the current state and decide the next agent to call.

Current state:
- Workflow has {node_count} nodes
- Categorization completed: {has_categorization}
- Best practices retrieved: {has_best_practices}
- Builder phase completed: {builder_completed}
- Configurator phase completed: {configurator_completed}

Last message: {last_message}

Decide which agent should act next:
- discovery: If we need to categorize and retrieve best practices
- builder: If we need to add nodes and connections
- configurator: If we need to configure node parameters
- responder: If we should respond to the user with results"""),
            ("human", "What's the next step?")
        ])
        
        structured_llm = self.llm.with_structured_output(SupervisorDecision)
        chain = prompt | structured_llm
        
        last_message = ""
        if state.get("messages"):
            last_msg = state["messages"][-1]
            last_message = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
        
        decision = await chain.ainvoke({
            "node_count": node_count,
            "has_categorization": has_categorization,
            "has_best_practices": has_best_practices,
            "builder_completed": "builder" in completed_phases,
            "configurator_completed": "configurator" in completed_phases,
            "last_message": last_message
        })
        
        return decision.next_agent