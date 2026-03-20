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
            elif technique.value == "notification":
                practices.append("- Use Email or Chat nodes for notifications")
                practices.append("- Include relevant data in messages")
            elif technique.value == "chatbot":
                practices.append("- Use Conversation node for chatbot interactions")
                practices.append("- Design clear conversation flows")
            elif technique.value == "form_input":
                practices.append("- Use Form node to gather user input")
                practices.append("- Validate form data before processing")
            elif technique.value == "scraping":
                practices.append("- Use HTTP Request node to fetch web data")
                practices.append("- Use Code node to parse HTML if needed")
            elif technique.value == "monitoring":
                practices.append("- Use Schedule trigger for regular checks")
                practices.append("- Use HTTP Request node to check service status")
            elif technique.value == "enrichment":
                practices.append("- Use API calls to enrich data with external sources")
                practices.append("- Cache enrichment results if possible")
            elif technique.value == "triage":
                practices.append("- Use If node to classify data based on criteria")
                practices.append("- Route data to different branches for processing")
            elif technique.value == "content_generation":
                practices.append("- Use AI nodes for generating text or content")
                practices.append("- Provide clear prompts for better results")
            elif technique.value == "document_processing":
                practices.append("- Use File nodes to handle documents")
                practices.append("- Use Code node for parsing and extracting data")
            elif technique.value == "data_extraction":
                practices.append("- Use Code node to extract specific information from data")
                practices.append("- Use regular expressions for pattern matching")
            elif technique.value == "data_analysis":
                practices.append("- Use Code node for data analysis and insights")
                practices.append("- Consider using external services for complex analysis")
            elif technique.value == "knowledge_base":
                practices.append("- Use Database nodes to build a knowledge base")
                practices.append("- Implement efficient querying for fast access")
            elif technique.value == "human_in_the_loop":
                practices.append("- Use Manual Trigger for human approval steps")
                practices.append("- Design clear instructions for human reviewers")
        
        return "\n".join(practices) if practices else "No specific best practices"

