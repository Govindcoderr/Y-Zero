# config.py
from typing import Dict, Any
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


class Config:
    # LLM Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "").strip()
    
    # Agent Configuration
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "5"))
    MAX_BUILDER_ITERATIONS = 15
    MAX_CONFIGURATOR_ITERATIONS = 10
    
    # Workflow Configuration
    DEFAULT_WORKFLOW_NAME = "New Workflow"
    NODE_HORIZONTAL_GAP = 280
    NODE_VERTICAL_GAP = 120
    INITIAL_NODE_X = 250
    INITIAL_NODE_Y = 300
    
    # Validation
    REQUIRE_TRIGGER_NODE = True
    REQUIRE_CONNECTED_NODES = True
    
    # 
    _ICON_BASE_URL =os.getenv("ICON_BASE_URL", "")


    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required")