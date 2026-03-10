# # backend/agents/greeter.py
# """
# GreeterAgent — Pipeline ka 1st Agent

# Kaam:
#   - User ka greeting (hi, hello, hey, etc.) detect karta hai
#   - Basic guide ya help request detect karta hai
#   - Agar greeting/guide hai → seedha respond karo, workflow building skip karo
#   - Agar real workflow request hai → aage jaane do

# Rules:
#   - Sirf greet aur guide karo, koi workflow mat banao
#   - Scope se bahar koi kaam mat karo (sirf n8n workflow builder ke baare mein baat karo)
#   - User ko clearly batao ki yeh tool kya kar sakta hai
# """

# from langchain_core.language_models import BaseChatModel
# from langchain_core.messages import SystemMessage, HumanMessage
# from typing import Dict, Any

# # ── System prompt ──────────────────────────────────────────────────────────────
# GREETER_SYSTEM_PROMPT = """You are the friendly front-desk assistant for an AI-powered n8n Workflow Builder.

# YOUR ROLE:
# You are the FIRST point of contact. Your job is to:
# 1. Warmly greet users
# 2. Explain what this tool can do
# 3. Guide them on how to use it properly
# 4. Decide if the user's message is a greeting/guide request OR a real workflow request

# WHAT THIS TOOL DOES:
# - Builds n8n automation workflows from natural language descriptions
# - Supports triggers: Schedule, Webhook, HTTP, Email, Cron
# - Supports actions: HTTP Request, Database, Email, Slack, File operations, Code execution
# - Supports conditionals: IF/Else branching, Switch, Merge
# - Connects nodes automatically
# - Validates the workflow structure

# WHAT THIS TOOL DOES NOT DO:
# - Cannot execute or run workflows (only builds them)
# - Cannot connect to live APIs or real databases
# - Cannot save workflows to your n8n instance directly
# - Cannot build non-workflow things (like websites, apps, or code projects)
# - Cannot answer questions unrelated to n8n workflow automation

# HOW TO USE THIS TOOL:
# Simply describe your automation in plain language. Examples:
#    "Create a workflow that fetches data from an API every hour and saves to database"
#    "Build a workflow triggered by webhook that sends a Slack message"
#    "Make a workflow that reads emails and processes attachments"
#    "Write me a Python script" (not a workflow request)
#    "What is the weather today?" (out of scope)

# DECISION RULES (VERY IMPORTANT):
# - If message is: hi, hello, hey, good morning, how are you, what can you do, help, guide me, what is this → respond warmly and explain the tool
# - If message is a real workflow automation request → respond with exactly: "PROCEED_TO_WORKFLOW"
# - If message is completely out of scope → politely say you can only help with n8n workflow building

# RESPONSE STYLE:
# - Warm, friendly, and helpful
# - Use emojis sparingly (1-2 max)
# - Keep responses concise but informative
# - Always end greeting responses with a prompt asking what workflow they'd like to build

# LANGUAGE:
# - Respond in the same language the user writes in (English, Hindi, Hinglish — match their style)
# """

# # ── Intent classifier prompt ───────────────────────────────────────────────────
# INTENT_SYSTEM_PROMPT = """You are an intent classifier for an n8n Workflow Builder tool.

# Classify the user's message into ONE of these categories:

# 1. GREETING - User is saying hi/hello or just starting a conversation
#    Examples: "hi", "hello", "hey there", "good morning", "what's up"

# 2. GUIDE_REQUEST - User wants to know what the tool does or how to use it
#    Examples: "what can you do?", "help me", "how does this work?", "guide me", "what is this tool?"

# 3. WORKFLOW_REQUEST - User wants to build an actual n8n workflow/automation
#    Examples: "create a workflow that...", "build automation for...", "make a pipeline that..."

# 4. OUT_OF_SCOPE - Request has nothing to do with n8n workflow automation
#    Examples: "write a poem", "what's the weather", "help me with my homework"

# Respond with ONLY one word: GREETING, GUIDE_REQUEST, WORKFLOW_REQUEST, or OUT_OF_SCOPE
# """


# class GreeterAgent:
#     """
#     First agent in the pipeline.
#     Handles greetings and basic guide requests.
#     Returns early WITHOUT triggering workflow building.
#     """

#     def __init__(self, llm: BaseChatModel):
#         self.llm = llm

#     async def classify_intent(self, user_message: str) -> str:
#         """
#         Classify the user's intent.
#         Returns: GREETING | GUIDE_REQUEST | WORKFLOW_REQUEST | OUT_OF_SCOPE
#         """
#         messages = [
#             SystemMessage(content=INTENT_SYSTEM_PROMPT),
#             HumanMessage(content=user_message),
#         ]
#         response = await self.llm.ainvoke(messages)
#         intent = response.content.strip().upper()

#         # Normalize to known values
#         valid_intents = {"GREETING", "GUIDE_REQUEST", "WORKFLOW_REQUEST", "OUT_OF_SCOPE"}
#         if intent not in valid_intents:
#             # Default: if unclear, treat as workflow request to avoid blocking real requests
#             return "WORKFLOW_REQUEST"
#         return intent

#     async def respond(self, user_message: str, intent: str) -> str:
#         """
#         Generate appropriate response based on intent.
#         """
#         messages = [
#             SystemMessage(content=GREETER_SYSTEM_PROMPT),
#             HumanMessage(content=f"[INTENT: {intent}]\nUser message: {user_message}"),
#         ]
#         response = await self.llm.ainvoke(messages)
#         return response.content.strip()

#     async def handle(self, user_message: str) -> Dict[str, Any]:
#         """
#         Main entry point.

#         Returns:
#             {
#                 "should_proceed": bool,   # True = continue to workflow pipeline
#                 "intent": str,            # Detected intent
#                 "response": str | None,   # Greeter's reply (None if should_proceed=True)
#             }
#         """
#         intent = await self.classify_intent(user_message)
#         print(f"🤝 Greeter: intent detected = {intent}")

#         if intent == "WORKFLOW_REQUEST":
#             # Real workflow request → let pipeline continue
#             return {
#                 "should_proceed": True,
#                 "intent": intent,
#                 "response": None,
#             }

#         # Greeting, Guide, or Out-of-scope → respond here, don't proceed
#         reply = await self.respond(user_message, intent)
#         return {
#             "should_proceed": False,
#             "intent": intent,
#             "response": reply,
#         }












# backend/agents/greeter.py
"""
GreeterAgent — Pipeline ka 1st Agent

Intents handled:
  GREETING          → Warm welcome + tool explanation
  GUIDE_REQUEST     → How-to guide
  WORKFLOW_REQUEST  → Forward to workflow pipeline (new build)
  WORKFLOW_MODIFY   → Forward to pipeline (existing workflow edit)
  WORKFLOW_QUESTION → Answer about current workflow state, no pipeline
  OUT_OF_SCOPE      → Polite refusal
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Intent classifier prompt
# ─────────────────────────────────────────────────────────────────────────────
INTENT_SYSTEM_PROMPT = """You are an intent classifier for an AI Workflow Builder tool.

Classify the user's message into EXACTLY ONE of these categories:

1. GREETING
   User is saying hi/hello OR combining a greeting WITH a question about the tool.
   Key signal: message starts with hi/hello/hey OR asks "how can I..." / "how do I..."
   Examples:
     "hi", "hello", "hey there", "good morning"
     "hi how can I build a workflow"      <- GREETING (asking HOW, not requesting a build)
     "hello how does this work"           <- GREETING
     "hey what can you do"                <- GREETING
     "hiii how I CAN BUILD A WORKFLOW"    <- GREETING (asking HOW, not requesting a build)

2. GUIDE_REQUEST
   User wants to understand the tool — no greeting, just asking about capabilities.
   Key signal: questions like "what can you do", "how does this work", "guide me"
   Examples:
     "what can you do?"
     "how does this work?"
     "guide me"
     "what workflows can you build?"
     "explain how to use this"

3. WORKFLOW_REQUEST
   User is giving a SPECIFIC automation task to build — not asking how, but telling what.
   Key signal: describes WHAT to automate with specific details (services, actions, data)
   Examples:
     "create a workflow that sends email every morning at 9am"
     "build automation that posts to Slack when I get a webhook"
     "make a pipeline that reads CSV and saves to database"
     "send daily Telegram message to my mom at 8am"
   NOT this: "how can I build a workflow" <- this is GREETING, user is asking HOW

4. WORKFLOW_MODIFY
   User wants to CHANGE an existing workflow.
   Key signal: refers to existing nodes/workflow with action words (add/remove/change/update)
   Examples:
     "add a Slack node", "remove the email node"
     "change the schedule to 8am", "update the message"
     "also send to WhatsApp", "delete the last node"

5. WORKFLOW_QUESTION
   User is asking ABOUT the current workflow state — not modifying.
   Examples:
     "what nodes do I have?", "show me the workflow"
     "how many nodes?", "is it connected properly?"

6. OUT_OF_SCOPE
   Nothing to do with workflow automation.
   Examples: "write a poem", "what's the weather", "tell me a joke"

CRITICAL RULES:
- "how can I build" / "how do I create" / "how to make" = GREETING (asking for guidance)
- "build a workflow that [specific task]" = WORKFLOW_REQUEST (actual build request)
- When message has BOTH greeting AND question about the tool -> always GREETING
- Respond with ONLY one word: GREETING, GUIDE_REQUEST, WORKFLOW_REQUEST, WORKFLOW_MODIFY, WORKFLOW_QUESTION, or OUT_OF_SCOPE
"""

# ─────────────────────────────────────────────────────────────────────────────
# Greeter response prompt
# ─────────────────────────────────────────────────────────────────────────────
GREETER_SYSTEM_PROMPT = """You are the friendly front-desk assistant for an AI-powered Workflow Builder.

YOUR ROLE:
You are the FIRST point of contact. Your job is to:
1. Warmly greet users
2. Explain what this tool can do
3. Guide them on how to use it properly

WHAT THIS TOOL DOES:
- Builds automation workflows from natural language descriptions
- Supports triggers: Schedule, Webhook, HTTP, Email, Manual
- Supports actions: HTTP Request, Telegram, Gmail, Slack, Database, Code, Set Node, and more
- Supports conditionals: IF/Else branching, Switch, Merge
- Connects nodes automatically
- You can ADD nodes, REMOVE nodes, UPDATE parameters — all by just chatting
- Validates the workflow structure

WHAT THIS TOOL DOES NOT DO:
- Cannot execute or run workflows (only builds them)
- Cannot connect to live APIs or real databases
- Cannot save workflows to your automation platform directly
- Cannot build non-workflow things (websites, apps, code projects)
- Cannot answer questions unrelated to workflow automation

HOW TO USE:
Simply describe your automation in plain language. Examples:
  "Create a workflow that fetches data from an API every hour and saves to database"
  "Build a workflow triggered by webhook that sends a Slack message"
  "Add a Telegram node that sends a morning message"
  "Remove the email node"
  "Change the schedule to 9am"

MULTI-TURN CONVERSATION:
Users can keep chatting to refine their workflow:
  Turn 1: "Make a daily Telegram message workflow"
  Turn 2: "Also add an error handler"
  Turn 3: "Change the time to 8am"
  Turn 4: "Remove the manual trigger"

RESPONSE STYLE:
- Warm, friendly, and helpful
- Use emojis sparingly (1-2 max)
- Keep responses concise but informative
- Always end with a prompt asking what they'd like to build or change

LANGUAGE:
- Respond in the same language the user writes in (English, Hindi, Hinglish — match their style)
"""


class GreeterAgent:
    """
    First agent in the pipeline.

    Handles greetings, guide requests, workflow questions, and out-of-scope.
    For WORKFLOW_REQUEST and WORKFLOW_MODIFY, sets should_proceed=True so the
    supervisor pipeline takes over.
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    async def classify_intent(self, user_message: str) -> str:
        """
        Classify user intent.
        Returns one of:
          GREETING | GUIDE_REQUEST | WORKFLOW_REQUEST |
          WORKFLOW_MODIFY | WORKFLOW_QUESTION | OUT_OF_SCOPE
        """
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=INTENT_SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ])
            intent = response.content.strip().upper()
        except Exception as e:
            print(f"⚠️  Intent classification failed: {e} — defaulting to WORKFLOW_REQUEST")
            return "WORKFLOW_REQUEST"

        valid = {
            "GREETING",
            "GUIDE_REQUEST",
            "WORKFLOW_REQUEST",
            "WORKFLOW_MODIFY",
            "WORKFLOW_QUESTION",
            "OUT_OF_SCOPE",
        }
        return intent if intent in valid else "WORKFLOW_REQUEST"

    async def respond(self, user_message: str, intent: str) -> str:
        """Generate a response for non-pipeline intents."""
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=GREETER_SYSTEM_PROMPT),
                HumanMessage(content=f"[INTENT: {intent}]\nUser message: {user_message}"),
            ])
            return response.content.strip()
        except Exception as e:
            print(f"⚠️  Greeter response failed: {e}")
            return "Hello! I'm your Workflow Builder assistant. Describe the automation you'd like to build!"

    async def handle(
        self,
        user_message: str,
        current_workflow: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point.

        Args:
            user_message:     Latest user message
            current_workflow: SimpleWorkflow object if a session exists (for QUESTION answers)

        Returns:
            {
                "should_proceed": bool,   # True → continue to supervisor pipeline
                "intent":         str,    # Detected intent
                "response":       str | None,  # Reply (None when should_proceed=True)
            }
        """
        intent = await self.classify_intent(user_message)
        print(f"🤝 Greeter: intent = {intent}")

        # ── Forward to pipeline ───────────────────────────────────
        if intent in ("WORKFLOW_REQUEST", "WORKFLOW_MODIFY"):
            return {
                "should_proceed": True,
                "intent": intent,
                "response": None,
            }

        # ── Answer workflow questions locally ─────────────────────
        if intent == "WORKFLOW_QUESTION":
            reply = self._answer_workflow_question(current_workflow)
            return {
                "should_proceed": False,
                "intent": intent,
                "response": reply,
            }

        # ── Greeting / Guide / Out-of-scope → respond here ────────
        reply = await self.respond(user_message, intent)
        return {
            "should_proceed": False,
            "intent": intent,
            "response": reply,
        }

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def _answer_workflow_question(self, workflow: Optional[Any]) -> str:
        """Build a human-readable answer about current workflow state."""
        if workflow is None or not workflow.nodes:
            return (
                "📭 No workflow has been built yet in this session.\n"
                "Describe what you'd like to automate and I'll build it for you!"
            )

        lines = [f"📊 **Current Workflow** — {len(workflow.nodes)} node(s):"]
        for i, node in enumerate(workflow.nodes, 1):
            lines.append(f"  {i}. **{node.name}** (`{node.type}` / {node.node_type})")

        # Edge summary
        edge_count = sum(
            len(arr) if arr else 0
            for conns in workflow.connections.values()
            for arrays in conns.values()
            for arr in arrays
        )
        lines.append(f"\n🔗 Connections: {edge_count} edge(s)")

        lines.append("\nYou can say things like:")
        lines.append('  • "Add a Slack node after the Telegram node"')
        lines.append('  • "Remove the SET node"')
        lines.append('  • "Change the schedule to every morning at 7am"')

        return "\n".join(lines)