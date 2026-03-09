
# # llm_provider.py
# from langchain_groq import ChatGroq
# import os
# import dotenv
# dotenv.load_dotenv()

# # ---------------------------------------------------------------
# # Groq models and their tool-calling support (Feb 2026)
# # ---------------------------------------------------------------
# # ✅ SUPPORTS tool calling:
# #   llama-3.3-70b-versatile
# #   llama3-groq-70b-8192-tool-use-preview
# #   llama3-groq-8b-8192-tool-use-preview
# #   llama-3.1-8b-instant
# #   llama3-70b-8192
# #   llama3-8b-8192
# #
# # ❌ NO tool calling:
# #   llama-3.1-70b-versatile   ← common mistake, looks similar but broken
# #   mixtral-8x7b-32768
# #   gemma2-9b-it
# #   gemma-7b-it
# # ---------------------------------------------------------------

# # These models are confirmed to support tool/function calling on Groq
# TOOL_CAPABLE_MODELS = {
#     "openai/gpt-oss-120b"
# }


# # Default — best balance of speed + capability for tool calling
# DEFAULT_TOOL_MODEL = "openai/gpt-oss-120b"
# # Default for non-tool tasks (discovery, categorization) — can be same or faster
# DEFAULT_FAST_MODEL = "openai/gpt-oss-120b"


# def _get_api_key() -> str:
#     api_key = os.getenv("GROQ_API_KEY", "").strip()
#     if not api_key:
#         raise ValueError(
#             "GROQ_API_KEY environment variable is not set. "
#             "Add it to your .env file: GROQ_API_KEY=gsk_..."
#         )
#     return api_key


# def get_llm(temperature: float = None) -> ChatGroq:
#     """
#     Return a Groq LLM that SUPPORTS tool/function calling.
    
#     The model is chosen by:
#       1. LLM_MODEL env var — BUT only if it's in TOOL_CAPABLE_MODELS
#       2. Otherwise falls back to DEFAULT_TOOL_MODEL (llama-3.3-70b-versatile)
    
#     This prevents accidentally using a non-tool model for the builder agent.
#     """
#     api_key = _get_api_key()
#     temp = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.1"))

#     requested = os.getenv("LLM_MODEL", "").strip()
#     if requested and requested in TOOL_CAPABLE_MODELS:
#         model = requested
#     else:
#         if requested and requested not in TOOL_CAPABLE_MODELS:
#             print(
#                 f"⚠️  LLM_MODEL='{requested}' does not support tool calling. "
#                 f"Falling back to '{DEFAULT_TOOL_MODEL}'."
#             )
#         model = DEFAULT_TOOL_MODEL

#     print(f"🤖 Tool LLM: {model}")
#     return ChatGroq(
#         model=model,
#         groq_api_key=api_key,
#         temperature=temp,
#         max_retries=2,
#     )


# def get_llm_no_tools(temperature: float = None) -> ChatGroq:
#     """
#     Return a Groq LLM for chains that do NOT use tools.
#     (discovery, categorization, intent generation, supervisor)
#     These don't need tool calling so any model works.
#     """
#     api_key = _get_api_key()
#     temp = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.1"))

#     # Prefer a fast model for non-tool tasks; fall back to default
#     model = os.getenv("LLM_MODEL_FAST", os.getenv("LLM_MODEL", DEFAULT_FAST_MODEL)).strip()

#     # If the env var is set to a non-tool model that's still valid for text, use it
#     # For non-tool tasks we accept any model
#     if not model:
#         model = DEFAULT_FAST_MODEL

#     print(f"🤖 Fast LLM: {model}")
#     return ChatGroq(
#         model=model,
#         groq_api_key=api_key,
#         temperature=temp,
#         max_retries=2,
#     )



# llm_provider.py — COMPLETE FILE REPLACE KARO

from langchain_groq import ChatGroq
import os
import dotenv
dotenv.load_dotenv()

# ── Models jo tool calling support karte hain ──────────────────
TOOL_CAPABLE_MODELS = {
    "llama-3.3-70b-versatile",
    "llama3-groq-70b-8192-tool-use-preview",
    "llama3-groq-8b-8192-tool-use-preview",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
}

# ── Models jo SIRF single HumanMessage accept karte hain ───────
# (text classification / audio — chat ke liye invalid)
_INVALID_CHAT_MODELS = {
    "whisper-large-v3",
    "whisper-large-v3-turbo",
    "distil-whisper-large-v3-en",
    "openai/gpt-oss-120b",   # text classification model — chat completions ke liye nahi
}

DEFAULT_TOOL_MODEL  = "llama-3.3-70b-versatile"
DEFAULT_FAST_MODEL  = "llama-3.3-70b-versatile"


def _get_api_key() -> str:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env")
    return api_key


def _safe_model(requested: str, valid_set: set, fallback: str, label: str) -> str:
    """
    Validate requested model. Falls back to `fallback` if:
    - empty
    - in _INVALID_CHAT_MODELS
    - not in valid_set (when valid_set is provided)
    """
    if not requested or requested in _INVALID_CHAT_MODELS:
        if requested:
            print(f"⚠️  {label}='{requested}' is not a valid chat model. Using '{fallback}'.")
        return fallback

    if valid_set and requested not in valid_set:
        print(f"⚠️  {label}='{requested}' not in tool-capable list. Using '{fallback}'.")
        return fallback

    return requested


def get_llm(temperature: float = None) -> ChatGroq:
    """Tool-calling capable LLM — for Builder and Configurator agents."""
    api_key = _get_api_key()
    temp = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.1"))

    requested = os.getenv("LLM_MODEL", DEFAULT_TOOL_MODEL).strip()
    model = _safe_model(requested, TOOL_CAPABLE_MODELS, DEFAULT_TOOL_MODEL, "LLM_MODEL")

    print(f"🤖 Tool LLM: {model}")
    return ChatGroq(
        model=model,
        groq_api_key=api_key,
        temperature=temp,
        max_retries=2,
    )


def get_llm_no_tools(temperature: float = None) -> ChatGroq:
    """Plain chat LLM — for Greeter, Discovery, Supervisor agents (no tool calling needed)."""
    api_key = _get_api_key()
    temp = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.1"))

    # LLM_MODEL_FAST → LLM_MODEL → DEFAULT_FAST_MODEL
    requested = os.getenv("LLM_MODEL_FAST", os.getenv("LLM_MODEL", DEFAULT_FAST_MODEL)).strip()
    # For no-tools we don't require tool capability, just valid chat model
    model = _safe_model(requested, set(), DEFAULT_FAST_MODEL, "LLM_MODEL_FAST")

    print(f"🤖 Fast LLM: {model}")
    return ChatGroq(
        model=model,
        groq_api_key=api_key,
        temperature=temp,
        max_retries=2,
    )