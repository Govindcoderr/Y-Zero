# config.py
from typing import Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()
class Config:
    # LLM Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL = "openai/gpt-oss-120b"
    LLM_TEMPERATURE = 0.2
    
    # Agent Configuration
    MAX_ITERATIONS = 10
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
    


    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required")