# # chains/categorization.py
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.language_models import BaseChatModel
# from langchain_core.output_parsers import PydanticOutputParser
# from pydantic import BaseModel, Field
# from typing import List
# from ..types.categorization import WorkflowTechnique, PromptCategorization, TECHNIQUE_DESCRIPTIONS

# class CategorizationOutput(BaseModel):
#     techniques: List[WorkflowTechnique] = Field(description="List of workflow techniques")
#     confidence: float = Field(description="Confidence score 0-1")
#     reasoning: str = Field(description="Explanation of the categorization")

# async def categorize_prompt(llm: BaseChatModel, user_prompt: str) -> PromptCategorization:
#     """Categorize user prompt into workflow techniques"""
    
#     parser = PydanticOutputParser(pydantic_object=CategorizationOutput)
    
#     techniques_text = "\n".join([
#         f"- {tech.value}: {desc}" 
#         for tech, desc in TECHNIQUE_DESCRIPTIONS.items()
#     ])
    
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are an expert workflow automation analyzer. 
#         Analyze the user's prompt and identify which workflow techniques are needed.

# Available Techniques:
# {techniques}

# Identify 0-5 relevant techniques with confidence score (0-1).

# {format_instructions}"""),
#         ("human", "{user_prompt}")
#     ])
    
#     chain = prompt | llm | parser
    
#     result = await chain.ainvoke({
#         "user_prompt": user_prompt,
#         "techniques": techniques_text,
#         "format_instructions": parser.get_format_instructions()
#     })
    
#     return PromptCategorization(
#         techniques=result.techniques,
#         confidence=result.confidence,
#         reasoning=result.reasoning
#     )




# chains/categorization.py
import json
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from typing import List
from ..types.categorization import WorkflowTechnique, PromptCategorization, TECHNIQUE_DESCRIPTIONS


def _extract_json(text: str) -> dict:
    """Extract first JSON object from LLM response."""
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


async def categorize_prompt(llm: BaseChatModel, user_prompt: str) -> PromptCategorization:
    """Categorize user prompt into workflow techniques using plain JSON output."""

    techniques_text = "\n".join(
        f"- {tech.value}: {desc}" for tech, desc in TECHNIQUE_DESCRIPTIONS.items()
    )
    valid_values = [t.value for t in WorkflowTechnique]

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a workflow automation analyzer.
Identify which techniques are needed for the user's request.

Available techniques:
{techniques_text}

Respond with ONLY a valid JSON object — no markdown, no explanation:
{{
  "techniques": ["technique1", "technique2"],
  "confidence": 0.9,
  "reasoning": "brief explanation"
}}

techniques must be values from: {valid_values}"""),
        ("human", "{user_prompt}"),
    ])

    try:
        chain = prompt | llm
        result = await chain.ainvoke({"user_prompt": user_prompt})
        content = result.content if hasattr(result, "content") else str(result)
        data = _extract_json(content)

        raw_techniques = data.get("techniques", [])
        techniques = []
        for t in raw_techniques:
            try:
                techniques.append(WorkflowTechnique(t))
            except ValueError:
                pass  # skip unknown values

        return PromptCategorization(
            techniques=techniques or [WorkflowTechnique.API_INTEGRATION],
            confidence=float(data.get("confidence", 0.7)),
            reasoning=data.get("reasoning", ""),
        )
    except Exception as e:
        return PromptCategorization(
            techniques=[WorkflowTechnique.API_INTEGRATION],
            confidence=0.5,
            reasoning=f"Fallback due to error: {e}",
        )