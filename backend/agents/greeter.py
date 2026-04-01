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

# .────────────────
# Intent classifier prompt
# .────────────────
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
   understand that they are asking for a general guide, not requesting a specific workflow build.
   Examples:
     "what can you do?"
     "how does this work?"
     "guide me"
     "what workflows can you build?"
     "explain how to use this"
     "can you help me with workflow automation?" (general guide request, not a specific build)
     "how can I use this tool?" (general guide request, not a specific build)"
     "what is this tool?" (general guide request, not a specific build)"
     "can you show me how to build a workflow?" (general guide request, not a specific build)
     "how do I create a workflow?" (general guide request, not a specific build)"
   NOT this: "how can I build a workflow" <- this is GREETING, user is asking HOW, not requesting a specific build

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
     "what does the workflow look like so far?"
     "can you summarize the workflow for me?"
     "what's the current workflow structure?"
     "what connections do I have?"
     "do I have any triggers set up?"
     "what actions are in my workflow?"
     "can you describe the workflow I've built so far?"
     "what's the status of my workflow?"
     "can you give me an overview of the workflow?"
     "what nodes and connections do I have?"
     "what does my workflow look like right now?"
     "how many nodes and edges do I have?"
     "can you summarize the current workflow structure?"
     "why use this node?" (asking about a specific node in the workflow, not requesting a build)
     "why not use this node?" (asking about a specific node in the workflow, not requesting a build)

    Always Answer  Format like this (concise but informative, not use emojis if it not fits): 


6. OUT_OF_SCOPE
   Nothing to do with workflow automation.
   Examples: 
   "write a poem", 
   "what's the weather", 
   "tell me a joke"
   "can you help me with my homework"
   "write me a Python script" (not a workflow request)",
   "what is the meaning of life?" (out of scope)",
   "who won the football match?" (out of scope)",
   "can you help me with my math problem?" (out of scope)",
   "what's the news today?" (out of scope)",
   "how do I cook pasta?" (out of scope)",
   "can you recommend a movie?" (out of scope)",
   "write a story about a dragon" (out of scope)",
   "what's the stock price of Apple?" (out of scope)"
    

CRITICAL RULES:
- "how can I build" / "how do I create" / "how to make" = GREETING (asking for guidance)
- "build a workflow that [specific task]" = WORKFLOW_REQUEST (actual build request)
- When message has BOTH greeting AND question about the tool -> always GREETING
- Respond with ONLY one word: GREETING, GUIDE_REQUEST, WORKFLOW_REQUEST, WORKFLOW_MODIFY, WORKFLOW_QUESTION, or OUT_OF_SCOPE
"""

# .────────────────
# Greeter response prompt
# .────────────────
GREETER_SYSTEM_PROMPT = """You are the friendly front-desk assistant for an AI-powered Workflow Builder.

YOUR ROLE:
You are the FIRST point of contact. Your job is to:
1. Warmly greet users
2. Explain what this tool can do
3. Guide them on how to use it properly

1. GREETING Format (strickly follow this template, no extra text):
     Respons like this(strick to the format, no extra text): :
        Hi there! 👋
        How can I help you with Y-Zero workflow automation today?
        Whether you want to:
        - Build a new workflow from scratch
        - Connect different apps and services
        - Automate a repetitive task
        - Integrate AI into your processes
        - Or just learn more about what Y-Zero can do
        Just let me know what you're looking to accomplish!

2. OUT_OF_SCOPE Format (strickly follow this template, no extra text):
     Respons like this(strick to the format, no extra text): :

        I appreciate your question, but I'm specifically designed to help you build and configure n8n workflows. 
        I don't have access to real-time information or the ability to search for current events like who the current Prime Minister of Pakistan is.

        However, if you're interested in building workflows that could help you stay updated on such information, I can help you create:

        News monitoring workflows that fetch updates from news APIs
        Web scraping workflows that pull information from specific websites
        RSS feed workflows that aggregate news from multiple sources
        Notification workflows that alert you when certain topics are mentioned
        
        Would you like me to help you build a workflow to automatically fetch and monitor news or information on topics you're interested in?



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

    # .─
    # Public API
    # .─

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

    # .─
    # Helpers
    # .─

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