# # llm_provider.py
# from langchain_groq import ChatGroq
# from backend.utils.config import Config

# def get_llm():
#     """Initialize and return Groq LLM instance"""
#     Config.validate()
    
#     return ChatGroq(
#         model=Config.LLM_MODEL,
#         groq_api_key=Config.GROQ_API_KEY,
#         temperature=Config.LLM_TEMPERATURE
#     )



# llm_provider.py
from langchain_groq import ChatGroq
import os

def get_llm():
    """Initialize and return Groq LLM instance"""
    # Get API key from environment variable
    api_key = os.getenv("GROQ_API_KEY","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")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    # Initialize ChatGroq with minimal parameters (no proxies)
    return ChatGroq(
        model=os.getenv("LLM_MODEL", "qwen/qwen3-32b"),
        groq_api_key=api_key,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_retries=2
    )