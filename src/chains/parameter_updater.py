# chains/parameter_updater.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseChatModel
from typing import Dict, Any, List
import json

async def update_node_parameters(
    llm: BaseChatModel,
    node_type: str,
    current_parameters: Dict[str, Any],
    node_properties: List[Dict[str, Any]],
    changes: List[str]
) -> Dict[str, Any]:
    """Update node parameters based on natural language changes"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are updating parameters for a {node_type} node.

Current parameters:
{current_parameters}

Node properties definition:
{node_properties}

Requested changes:
{changes}

Return ONLY a valid JSON object with the complete updated parameters.
Include all existing parameters plus the requested changes."""),
        ("human", "Update the parameters as requested.")
    ])
    
    chain = prompt | llm
    
    result = await chain.ainvoke({
        "node_type": node_type,
        "current_parameters": json.dumps(current_parameters, indent=2),
        "node_properties": json.dumps(node_properties, indent=2),
        "changes": "\n".join(f"{i+1}. {change}" for i, change in enumerate(changes))
    })
    
    # Parse JSON from response
    content = result.content
    if isinstance(content, str):
        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return json.loads(content)
    
    return content