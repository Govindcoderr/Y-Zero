# # chains/intent_generation.py
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.language_models import BaseChatModel
# from pydantic import BaseModel, Field
# from typing import List

# class IntentOutput(BaseModel):
#     primary_goal: str = Field(description="Main objective of the workflow")
#     key_actions: List[str] = Field(description="List of actions needed")
#     data_sources: List[str] = Field(description="Data sources or inputs")
#     data_destinations: List[str] = Field(description="Where data should go")
#     conditions: List[str] = Field(description="Logical conditions or rules")
#     expected_output: str = Field(description="What the workflow should produce")

# async def generate_intent(llm: BaseChatModel, user_prompt: str) -> IntentOutput:
#     """Extract structured intent from user prompt"""
    
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are a workflow intent analyzer. 
#         Extract the core intent and requirements from the user's request.
        
#         Provide structured analysis of:
#         1. Primary goal
#         2. Key actions needed
#         3. Data sources/inputs
#         4. Data destinations/outputs
#         5. Conditions or logic
#         6. Expected final output"""),
#         ("human", "{user_prompt}")
#     ])
    
#     structured_llm = llm.with_structured_output(IntentOutput)
#     chain = prompt | structured_llm
    
#     return await chain.ainvoke({"user_prompt": user_prompt})





# chains/intent_generation.py
import json
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field
from typing import List


class IntentOutput(BaseModel):
    primary_goal: str = Field(default="")
    key_actions: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    data_destinations: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    expected_output: str = Field(default="")


def _extract_json(text: str) -> dict:
    """Extract first JSON object from LLM response, stripping markdown fences."""
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


async def generate_intent(llm: BaseChatModel, user_prompt: str) -> IntentOutput:
    """Extract structured intent from user prompt using plain JSON output (no tool calling)."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a workflow intent analyzer. Extract intent from the user's request.

Respond with ONLY a valid JSON object — no markdown, no explanation, no code fences:
{{
  "primary_goal": "string",
  "key_actions": ["action1", "action2"],
  "data_sources": ["source1"],
  "data_destinations": ["dest1"],
  "conditions": ["condition1"],
  "expected_output": "string"
}}"""),
        ("human", "{user_prompt}"),
    ])

    try:
        chain = prompt | llm
        result = await chain.ainvoke({"user_prompt": user_prompt})
        content = result.content if hasattr(result, "content") else str(result)
        data = _extract_json(content)
        return IntentOutput(
            primary_goal=data.get("primary_goal", user_prompt),
            key_actions=data.get("key_actions", []),
            data_sources=data.get("data_sources", []),
            data_destinations=data.get("data_destinations", []),
            conditions=data.get("conditions", []),
            expected_output=data.get("expected_output", ""),
        )
    except Exception as e:
        # Graceful fallback — discovery still works even if intent parse fails
        return IntentOutput(primary_goal=user_prompt)