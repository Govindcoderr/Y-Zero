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



# """Discovery Agent - Analyzes user prompts and categorizes workflow needs"""
# from typing import Dict, Any
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import JsonOutputParser
# from backend.types.categorization import WorkflowCategorization, WorkflowTechnique
# from backend.chains.categorization import BestPractices
# import json
# import re

# class DiscoveryAgent:
#     """Agent responsible for analyzing user requests"""
    
#     def __init__(self, llm):
#         self.llm = llm
#         self.categorization_chain = self._create_categorization_chain()
#         self.best_practices_chain = self._create_best_practices_chain()
    
#     def _create_categorization_chain(self):
#         """Create the prompt categorization chain"""
        
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", """You are a workflow categorization expert. Analyze the user's request and identify which workflow techniques are needed.

# Available techniques:
# - scheduling: Running actions at specific times or intervals
# - api_integration: Connecting to external APIs and services
# - data_transformation: Cleaning, formatting, or restructuring data
# - notification: Sending alerts via email, chat, SMS, or other channels
# - chatbot: Building conversational interfaces
# - form_input: Gathering data from users through forms
# - scraping: Collecting data from websites
# - monitoring: Checking service status and health
# - enrichment: Adding extra data from other sources
# - triage: Classifying and routing data based on criteria
# - content_generation: Creating text, images, videos, or other content
# - document_processing: Working with PDFs, Word docs, spreadsheets
# - data_extraction: Pulling specific information from data sources
# - data_analysis: Finding patterns, insights, and statistics
# - knowledge_base: Building and querying information databases
# - human_in_the_loop: Requiring human approval or input

# CRITICAL INSTRUCTIONS:
# 1. You MUST respond with ONLY valid JSON
# 2. Do NOT include any explanatory text before or after the JSON
# 3. Do NOT use <think> tags or any other XML tags
# 4. Start your response directly with {{ and end with }}
# 5. The JSON must have these exact fields: techniques, confidence, reasoning

# Example valid response:
# {{"techniques": ["scheduling", "api_integration"], "confidence": 0.9, "reasoning": "Requires scheduled API calls"}}

# Now analyze this request and respond with ONLY the JSON object:"""),
#             ("user", "{user_prompt}")
#         ])
        
#         return prompt | self.llm
    
#     def _create_best_practices_chain(self):
#         """Create the best practices recommendation chain"""
        
#         prompt = ChatPromptTemplate.from_messages([
#             ("system", """You are a workflow design expert. Given the workflow techniques needed, provide best practices.

# CRITICAL: Respond with ONLY valid JSON. No explanatory text, no think tags, just pure JSON.

# Output format:
# {{
#   "error_handling": ["practice1", "practice2"],
#   "performance": ["practice1", "practice2"],
#   "security": ["practice1", "practice2"],
#   "maintainability": ["practice1", "practice2"]
# }}"""),
#             ("user", "Techniques: {techniques}\n\nProvide best practices in JSON format:")
#         ])
        
#         return prompt | self.llm
    
#     def _extract_json_from_response(self, text: str) -> dict:
#         """Extract JSON from response that may contain extra text"""
        
#         # Remove <think> tags and their content
#         text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
#         # Remove text before first {
#         text = re.sub(r'^.*?(?=\{)', '', text, flags=re.DOTALL)
        
#         # Remove text after last }
#         text = re.sub(r'\}[^}]*$', '}', text, flags=re.DOTALL)
        
#         # Try to parse
#         try:
#             return json.loads(text.strip())
#         except json.JSONDecodeError:
#             # Try to find JSON object with nested structures
#             brace_count = 0
#             start_idx = text.find('{')
#             if start_idx == -1:
#                 raise ValueError("No JSON object found")
            
#             for i, char in enumerate(text[start_idx:], start=start_idx):
#                 if char == '{':
#                     brace_count += 1
#                 elif char == '}':
#                     brace_count -= 1
#                     if brace_count == 0:
#                         json_str = text[start_idx:i+1]
#                         return json.loads(json_str)
            
#             raise ValueError("Could not extract valid JSON")
    
#     async def analyze(self, user_message: str) -> Dict[str, Any]:
#         """
#         Analyze user message and return categorization and best practices
        
#         Args:
#             user_message: The user's workflow request
            
#         Returns:
#             Dict containing categorization and best practices
#         """
        
#         # Step 1: Categorize the prompt
#         try:
#             response = await self.categorization_chain.ainvoke({
#                 "user_prompt": user_message
#             })
            
#             # Extract content from response
#             if hasattr(response, 'content'):
#                 response_text = response.content
#             else:
#                 response_text = str(response)
            
#             # Parse JSON with fallback extraction
#             try:
#                 categorization_data = json.loads(response_text)
#             except json.JSONDecodeError:
#                 print(f"Failed to parse JSON directly, attempting extraction...")
#                 categorization_data = self._extract_json_from_response(response_text)
            
#             # Create categorization object
#             techniques = [
#                 WorkflowTechnique(t) for t in categorization_data.get("techniques", [])
#             ]
            
#             categorization = WorkflowCategorization(
#                 techniques=techniques,
#                 confidence=categorization_data.get("confidence", 0.5),
#                 reasoning=categorization_data.get("reasoning", "Analysis completed")
#             )
            
#         except Exception as e:
#             print(f"Categorization error: {e}, using fallback")
#             # Fallback categorization
#             categorization = WorkflowCategorization(
#                 techniques=[WorkflowTechnique.API_INTEGRATION, WorkflowTechnique.DATA_TRANSFORMATION],
#                 confidence=0.5,
#                 reasoning=f"Fallback categorization due to error: {str(e)}"
#             )
        
#         # Step 2: Get best practices
#         try:
#             techniques_str = ", ".join([t.value for t in categorization.techniques])
            
#             response = await self.best_practices_chain.ainvoke({
#                 "techniques": techniques_str
#             })
            
#             if hasattr(response, 'content'):
#                 response_text = response.content
#             else:
#                 response_text = str(response)
            
#             # Parse JSON with fallback extraction
#             try:
#                 practices_data = json.loads(response_text)
#             except json.JSONDecodeError:
#                 practices_data = self._extract_json_from_response(response_text)
            
#             best_practices = BestPractices(
#                 error_handling=practices_data.get("error_handling", []),
#                 performance=practices_data.get("performance", []),
#                 security=practices_data.get("security", []),
#                 maintainability=practices_data.get("maintainability", [])
#             )
            
#         except Exception as e:
#             print(f"Best practices error: {e}, using defaults")
#             # Fallback best practices
#             best_practices = BestPractices(
#                 error_handling=["Add error handling for API calls"],
#                 performance=["Optimize data processing"],
#                 security=["Validate all inputs"],
#                 maintainability=["Add clear node naming"]
#             )
        
#         return {
#             "categorization": categorization,
#             "best_practices": best_practices,
#             "summary": f"Identified {len(categorization.techniques)} workflow techniques with {categorization.confidence:.0%} confidence"
#         }