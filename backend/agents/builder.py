# agents/builder.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from typing import List, Any, Dict

class BuilderAgent:
    """Agent responsible for building workflow structure"""
    
    def __init__(
        self, 
        llm: BaseChatModel, 
        tools: List[Any],
        search_engine
    ):
        self.llm = llm
        self.tools = tools
        self.search_engine = search_engine
    
    async def build_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Build workflow by adding and connecting nodes"""
        
        workflow_summary = self._create_workflow_summary(state)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert workflow builder. Build the workflow by analyzing requirements.

Current workflow state:
{workflow_summary}

Best practices:
{best_practices}

Identified techniques:
{techniques}

Analyze the workflow and provide recommendations."""),
            ("human", "{input}"),
        ])
        
        # For now, use a simple LLM call instead of complex agent
        chain = prompt | self.llm

        # Safely extract last user message content (support dicts and message objects)
        last_message = None
        if state.get("messages"):
            last_message = state.get("messages")[-1]

        if last_message is None:
            user_input = "Build the workflow"
        else:
            if isinstance(last_message, dict):
                user_input = last_message.get("content") or last_message.get("text") or "Build the workflow"
            else:
                user_input = getattr(last_message, "content", None) or getattr(last_message, "text", None) or str(last_message)

        # Extract techniques safely (supports PromptCategorization dataclass or dict)
        techniques_list = self._extract_techniques(state)

        result = await chain.ainvoke({
            "input": user_input,
            "workflow_summary": workflow_summary,
            "best_practices": state.get("best_practices", ""),
            "techniques": ", ".join([t.value if hasattr(t, 'value') else (t.get('value', t) if isinstance(t, dict) else str(t)) for t in techniques_list]),
        })
        
        return {
            "summary": result.content if hasattr(result, 'content') else str(result),
            "nodes_added": len(state["workflow_json"].nodes)
        }
    
    def _create_workflow_summary(self, state: Dict[str, Any]) -> str:
        """Create human-readable workflow summary"""
        workflow = state["workflow_json"]
        
        if not workflow.nodes:
            return "Empty workflow - no nodes yet"
        
        summary = [f"Workflow: {workflow.name}"]
        summary.append(f"Nodes ({len(workflow.nodes)}):")
        
        for node in workflow.nodes:
            summary.append(f"  - {node.name} ({node.type})")
        
        if workflow.connections:
            summary.append(f"Connections ({sum(len(conns) for conns in workflow.connections.values())}):")
            for source, connections in workflow.connections.items():
                for conn_type, conn_list in connections.items():
                    for conn_array in conn_list:
                        for conn in conn_array:
                            summary.append(f"  - {source} → {conn.node}")
        
        return "\n".join(summary)

    def _extract_techniques(self, state: Dict[str, Any]):
        """Return list of techniques from state, handling dataclasses and dicts."""
        cat = state.get("categorization")
        if cat is None:
            return []
        # If it's a dataclass/object with attribute `techniques`
        if hasattr(cat, "techniques"):
            return getattr(cat, "techniques") or []
        # If it's a dict-like
        if isinstance(cat, dict):
            return cat.get("techniques", []) or []
        # Fallback
        return []