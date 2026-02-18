# agents/configurator.py
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List

class ConfiguratorAgent:
    """Agent responsible for configuring node parameters"""
    
    def __init__(self, llm: BaseChatModel, tools: List[Any]):
        self.llm = llm
        self.tools = tools
    
    async def configure_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Configure node parameters based on requirements"""
        
        workflow = state["workflow_json"]
        
        # Identify nodes needing configuration
        nodes_to_configure = [
            node for node in workflow.nodes 
            if not node.parameters or len(node.parameters) == 0
        ]
        
        if not nodes_to_configure:
            return {
                "summary": "All nodes are already configured",
                "nodes_configured": 0
            }
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a workflow configuration expert.

Current workflow:
{workflow_summary}

Nodes needing configuration:
{nodes_to_configure}

Provide configuration recommendations for each node."""),
            ("human", "{input}"),
        ])
        
        # Use simple LLM call instead of complex agent
        chain = prompt | self.llm

        # Safely extract last user message content (support dicts and message objects)
        last_message = None
        if state.get("messages"):
            last_message = state.get("messages")[-1]

        if last_message is None:
            user_input = "Configure the workflow"
        else:
            if isinstance(last_message, dict):
                user_input = last_message.get("content") or last_message.get("text") or "Configure the workflow"
            else:
                user_input = getattr(last_message, "content", None) or getattr(last_message, "text", None) or str(last_message)

        result = await chain.ainvoke({
            "input": user_input,
            "workflow_summary": self._create_workflow_summary(workflow),
            "nodes_to_configure": "\n".join([f"- {node.name} ({node.type})" for node in nodes_to_configure])
        })
        
        return {
            "summary": result.content if hasattr(result, 'content') else str(result),
            "nodes_configured": len(nodes_to_configure)
        }
    
    def _create_workflow_summary(self, workflow) -> str:
        """Create workflow summary"""
        summary = [f"Workflow: {workflow.name}"]
        summary.append(f"Total nodes: {len(workflow.nodes)}")
        
        if workflow.nodes:
            summary.append("Nodes:")
            for node in workflow.nodes:
                summary.append(f"  - {node.name} ({node.type})")
        
        return "\n".join(summary)