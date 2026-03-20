# llm_provider.py — COMPLETE FILE REPLACE KARO

from langchain_groq import ChatGroq
from backend.utils.config import Config 
import os



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
    api_key =Config.GROQ_API_KEY
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
    temp = temperature if temperature is not None else float(Config.LLM_TEMPERATURE)

    requested = Config.LLM_MODEL or DEFAULT_TOOL_MODEL
    model = _safe_model(requested, TOOL_CAPABLE_MODELS, DEFAULT_TOOL_MODEL, "LLM_MODEL")

    print(f"-->Tool LLM: {model}")
    return ChatGroq(
        model=model,
        groq_api_key=api_key,
        temperature=temp,
        max_retries=2,
    )


def get_llm_no_tools(temperature: float = None) -> ChatGroq:
    """Plain chat LLM — for Greeter, Discovery, Supervisor agents (no tool calling needed)."""
    api_key = _get_api_key()
    temp = temperature if temperature is not None else float(Config.LLM_TEMPERATURE)

    # LLM_MODEL_FAST → LLM_MODEL → DEFAULT_FAST_MODEL
    requested = Config.LLM_MODEL_FAST or Config.LLM_MODEL or DEFAULT_FAST_MODEL
    # For no-tools we don't require tool capability, just valid chat model
    model = _safe_model(requested, set(), DEFAULT_FAST_MODEL, "LLM_MODEL_FAST")

    print(f"-->Fast LLM: {model}")
    return ChatGroq(
        model=model,
        groq_api_key=api_key,
        temperature=temp,
        max_retries=2,
    )