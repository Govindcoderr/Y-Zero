#
from langchain_groq import ChatGroq
import os

def get_llm():
    """Initialize and return Groq LLM instance"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    
    model = os.getenv("LLM_MODEL", "llama-3.1-70b-versatile")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    
    # NO JSON mode when using tools!
    return ChatGroq(
        model=model,
        groq_api_key=api_key,
        temperature=temperature,  # Very low = focused output
        max_retries=2
    )

# # llm_provider.py
# from langchain_groq import ChatGroq
# import os

# def get_llm():
#     """Initialize and return Groq LLM instance"""
#     # Get API key from environment variable
#     api_key = os.getenv("GROQ_API_KEY","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")
#     if not api_key:
#         raise ValueError("GROQ_API_KEY environment variable not set")
    
#     # Initialize ChatGroq with minimal parameters (no proxies)
#     return ChatGroq(
#         model=os.getenv("LLM_MODEL", "qwen/qwen3-32b"),
#         groq_api_key=api_key,
#         temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
#         max_retries=2
#     )