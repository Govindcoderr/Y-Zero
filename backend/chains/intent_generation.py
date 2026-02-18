# chains/intent_generation.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field
from typing import List

class IntentOutput(BaseModel):
    primary_goal: str = Field(description="Main objective of the workflow")
    key_actions: List[str] = Field(description="List of actions needed")
    data_sources: List[str] = Field(description="Data sources or inputs")
    data_destinations: List[str] = Field(description="Where data should go")
    conditions: List[str] = Field(description="Logical conditions or rules")
    expected_output: str = Field(description="What the workflow should produce")

async def generate_intent(llm: BaseChatModel, user_prompt: str) -> IntentOutput:
    """Extract structured intent from user prompt"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a workflow intent analyzer. 
        Extract the core intent and requirements from the user's request.
        
        Provide structured analysis of:
        1. Primary goal
        2. Key actions needed
        3. Data sources/inputs
        4. Data destinations/outputs
        5. Conditions or logic
        6. Expected final output"""),
        ("human", "{user_prompt}")
    ])
    
    structured_llm = llm.with_structured_output(IntentOutput)
    chain = prompt | structured_llm
    
    return await chain.ainvoke({"user_prompt": user_prompt})