# backend/agents/greeter.py
"""
GreeterAgent — Pipeline ka 1st Agent

Kaam:
  - User ka greeting (hi, hello, hey, etc.) detect karta hai
  - Basic guide ya help request detect karta hai
  - Agar greeting/guide hai → seedha respond karo, workflow building skip karo
  - Agar real workflow request hai → aage jaane do

Rules:
  - Sirf greet aur guide karo, koi workflow mat banao
  - Scope se bahar koi kaam mat karo (sirf n8n workflow builder ke baare mein baat karo)
  - User ko clearly batao ki yeh tool kya kar sakta hai
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any

# ── System prompt ──────────────────────────────────────────────────────────────
GREETER_SYSTEM_PROMPT = """You are the friendly front-desk assistant for an AI-powered n8n Workflow Builder.

YOUR ROLE:
You are the FIRST point of contact. Your job is to:
1. Warmly greet users
2. Explain what this tool can do
3. Guide them on how to use it properly
4. Decide if the user's message is a greeting/guide request OR a real workflow request

WHAT THIS TOOL DOES:
- Builds n8n automation workflows from natural language descriptions
- Supports triggers: Schedule, Webhook, HTTP, Email, Cron
- Supports actions: HTTP Request, Database, Email, Slack, File operations, Code execution
- Supports conditionals: IF/Else branching, Switch, Merge
- Connects nodes automatically
- Validates the workflow structure

WHAT THIS TOOL DOES NOT DO:
- Cannot execute or run workflows (only builds them)
- Cannot connect to live APIs or real databases
- Cannot save workflows to your n8n instance directly
- Cannot build non-workflow things (like websites, apps, or code projects)
- Cannot answer questions unrelated to n8n workflow automation

HOW TO USE THIS TOOL:
Simply describe your automation in plain language. Examples:
   "Create a workflow that fetches data from an API every hour and saves to database"
   "Build a workflow triggered by webhook that sends a Slack message"
   "Make a workflow that reads emails and processes attachments"
   "Write me a Python script" (not a workflow request)
   "What is the weather today?" (out of scope)

DECISION RULES (VERY IMPORTANT):
- If message is: hi, hello, hey, good morning, how are you, what can you do, help, guide me, what is this → respond warmly and explain the tool
- If message is a real workflow automation request → respond with exactly: "PROCEED_TO_WORKFLOW"
- If message is completely out of scope → politely say you can only help with n8n workflow building

RESPONSE STYLE:
- Warm, friendly, and helpful
- Use emojis sparingly (1-2 max)
- Keep responses concise but informative
- Always end greeting responses with a prompt asking what workflow they'd like to build

LANGUAGE:
- Respond in the same language the user writes in (English, Hindi, Hinglish — match their style)
"""

# ── Intent classifier prompt ───────────────────────────────────────────────────
INTENT_SYSTEM_PROMPT = """You are an intent classifier for an n8n Workflow Builder tool.

Classify the user's message into ONE of these categories:

1. GREETING - User is saying hi/hello or just starting a conversation
   Examples: "hi", "hello", "hey there", "good morning", "what's up"

2. GUIDE_REQUEST - User wants to know what the tool does or how to use it
   Examples: "what can you do?", "help me", "how does this work?", "guide me", "what is this tool?"

3. WORKFLOW_REQUEST - User wants to build an actual n8n workflow/automation
   Examples: "create a workflow that...", "build automation for...", "make a pipeline that..."

4. OUT_OF_SCOPE - Request has nothing to do with n8n workflow automation
   Examples: "write a poem", "what's the weather", "help me with my homework"

Respond with ONLY one word: GREETING, GUIDE_REQUEST, WORKFLOW_REQUEST, or OUT_OF_SCOPE
"""


class GreeterAgent:
    """
    First agent in the pipeline.
    Handles greetings and basic guide requests.
    Returns early WITHOUT triggering workflow building.
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def classify_intent(self, user_message: str) -> str:
        """
        Classify the user's intent.
        Returns: GREETING | GUIDE_REQUEST | WORKFLOW_REQUEST | OUT_OF_SCOPE
        """
        messages = [
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
        response = await self.llm.ainvoke(messages)
        intent = response.content.strip().upper()

        # Normalize to known values
        valid_intents = {"GREETING", "GUIDE_REQUEST", "WORKFLOW_REQUEST", "OUT_OF_SCOPE"}
        if intent not in valid_intents:
            # Default: if unclear, treat as workflow request to avoid blocking real requests
            return "WORKFLOW_REQUEST"
        return intent

    async def respond(self, user_message: str, intent: str) -> str:
        """
        Generate appropriate response based on intent.
        """
        messages = [
            SystemMessage(content=GREETER_SYSTEM_PROMPT),
            HumanMessage(content=f"[INTENT: {intent}]\nUser message: {user_message}"),
        ]
        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    async def handle(self, user_message: str) -> Dict[str, Any]:
        """
        Main entry point.

        Returns:
            {
                "should_proceed": bool,   # True = continue to workflow pipeline
                "intent": str,            # Detected intent
                "response": str | None,   # Greeter's reply (None if should_proceed=True)
            }
        """
        intent = await self.classify_intent(user_message)
        print(f"🤝 Greeter: intent detected = {intent}")

        if intent == "WORKFLOW_REQUEST":
            # Real workflow request → let pipeline continue
            return {
                "should_proceed": True,
                "intent": intent,
                "response": None,
            }

        # Greeting, Guide, or Out-of-scope → respond here, don't proceed
        reply = await self.respond(user_message, intent)
        return {
            "should_proceed": False,
            "intent": intent,
            "response": reply,
        }