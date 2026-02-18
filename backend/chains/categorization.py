# chains/categorization.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List
from ..types.categorization import WorkflowTechnique, PromptCategorization, TECHNIQUE_DESCRIPTIONS

class CategorizationOutput(BaseModel):
    techniques: List[WorkflowTechnique] = Field(description="List of workflow techniques")
    confidence: float = Field(description="Confidence score 0-1")
    reasoning: str = Field(description="Explanation of the categorization")

async def categorize_prompt(llm: BaseChatModel, user_prompt: str) -> PromptCategorization:
    """Categorize user prompt into workflow techniques"""
    
    parser = PydanticOutputParser(pydantic_object=CategorizationOutput)
    
    techniques_text = "\n".join([
        f"- {tech.value}: {desc}" 
        for tech, desc in TECHNIQUE_DESCRIPTIONS.items()
    ])
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert workflow automation analyzer. 
        Analyze the user's prompt and identify which workflow techniques are needed.

Available Techniques:
{techniques}

Identify 0-5 relevant techniques with confidence score (0-1).

{format_instructions}"""),
        ("human", "{user_prompt}")
    ])
    
    chain = prompt | llm | parser
    
    result = await chain.ainvoke({
        "user_prompt": user_prompt,
        "techniques": techniques_text,
        "format_instructions": parser.get_format_instructions()
    })
    
    return PromptCategorization(
        techniques=result.techniques,
        confidence=result.confidence,
        reasoning=result.reasoning
    )