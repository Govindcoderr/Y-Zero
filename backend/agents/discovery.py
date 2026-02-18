# agents/discovery.py
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models import BaseChatModel
from backend.chains.categorization import categorize_prompt
from backend.chains.intent_generation import generate_intent
from typing import Dict, Any

class DiscoveryAgent:
    """Agent responsible for analyzing user intent and categorizing workflow type"""
    
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
    
    async def analyze(self, user_prompt: str) -> Dict[str, Any]:
        """Analyze user prompt and categorize workflow"""
        
        # Generate intent
        intent = await generate_intent(self.llm, user_prompt)
        
        # Categorize prompt
        categorization = await categorize_prompt(self.llm, user_prompt)
        
        # Get best practices (simplified - in production would fetch from knowledge base)
        best_practices = self._get_best_practices(categorization.techniques)
        
        return {
            "intent": intent,
            "categorization": categorization,
            "best_practices": best_practices,
            "summary": f"Identified techniques: {', '.join([t.value for t in categorization.techniques])}"
        }
    
    def _get_best_practices(self, techniques) -> str:
        """Retrieve best practices for identified techniques"""
        practices = []
        
        for technique in techniques:
            if technique.value == "scheduling":
                practices.append("- Use schedule trigger for time-based workflows")
                practices.append("- Set appropriate time zones")
            elif technique.value == "api_integration":
                practices.append("- Use HTTP Request node for API calls")
                practices.append("- Handle authentication properly")
                practices.append("- Implement error handling")
            elif technique.value == "data_transformation":
                practices.append("- Use Set node for field mapping")
                practices.append("- Use Code node for complex transformations")
            # Add more as needed
        
        return "\n".join(practices) if practices else "No specific best practices"