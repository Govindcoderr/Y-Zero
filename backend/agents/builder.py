
# # agents/builder.py
# import re
# import json
# from langchain_core.language_models import BaseChatModel
# from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
# from typing import List, Any, Dict

# #
# # JSON comment/trailing-comma stripper#
# def strip_json_comments(text: str) -> str:
#     result = []
#     i, n, in_string = 0, len(text), False
#     while i < n:
#         c = text[i]
#         if c == '"' and (i == 0 or text[i - 1] != '\\'):
#             in_string = not in_string
#             result.append(c); i += 1; continue
#         if in_string:
#             result.append(c); i += 1; continue
#         if c == '/' and i + 1 < n:
#             if text[i + 1] == '/':
#                 while i < n and text[i] != '\n': i += 1
#                 continue
#             if text[i + 1] == '*':
#                 i += 2
#                 while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'): i += 1
#                 i += 2; continue
#         result.append(c); i += 1
#     cleaned = ''.join(result)
#     cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
#     return cleaned.strip()


# def sanitize_tool_calls(response: AIMessage) -> AIMessage:
#     if not getattr(response, 'tool_calls', None):
#         return response
#     fixed = []
#     for tc in response.tool_calls:
#         args = tc.get('args', {})
#         if isinstance(args, str):
#             try: args = json.loads(strip_json_comments(args))
#             except: args = {}
#         if isinstance(args, dict):
#             try: args = json.loads(strip_json_comments(json.dumps(args)))
#             except: pass
#         fixed.append({**tc, 'args': args})
#     response.tool_calls = fixed
#     return response

# #
# # BuilderAgent#
# class BuilderAgent:

#     def __init__(self, llm: BaseChatModel, tools: List[Any], search_engine):
#         self.llm = llm
#         self.tools = tools
#         self.search_engine = search_engine
#         self.llm_with_tools = llm.bind_tools(tools) if tools else llm
#         # Build a quick tool lookup map
#         self._tool_map = {t.name: t for t in tools}

#     async def build_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         workflow   = state["workflow_json"]
#         user_input = self._extract_last_user_message(state)

#         # ── Build compact node catalogue for prompt ───────────────
#         all_nodes  = self.search_engine.get_all_node_names()
#         triggers   = [n for n in all_nodes if n["nodeType"] == "trigger"]
#         actions    = [n for n in all_nodes if n["nodeType"] == "action"]
#         conds      = [n for n in all_nodes if n["nodeType"] == "conditional"]

#         def fmt(lst): return ", ".join(n["name"] for n in lst)

#         system_prompt = f"""You are a workflow builder. Build a complete workflow for the user's request.

# AVAILABLE NODES
#   Triggers    (start the workflow): {fmt(triggers)}
#   Actions     (do something):       {fmt(actions)}
#   Conditionals (branch the flow):   {fmt(conds)}

# ROLE SELECTION RULES (critical):
#   role='trigger'     → SIRF pehle/start node ke liye
#   role='action'      → Beech mein ya end mein koi bhi node
#                        MailChimp/Gmail/Slack beech mein → HAMESHA role='action'
#   role='conditional' → IF, SWITCH, FILTER only
  
# RULES — follow exactly, no exceptions:
# 1. FIRST node MUST always be a Trigger — NO EXCEPTIONS.
#    - Trigger choose karne ka STRICT rule (in order check karo):
     
#       SCHEDULE TRIGGER — IN CASES MEIN USE KARO (MANDATORY):
#        * User ne kaha: "every hour", "every day", "daily", "hourly"
#        * User ne kaha: "every X minutes/seconds/weeks"
#        * User ne kaha: "at 9am", "every morning", "every night"
#        * User ne kaha: "automatically", "periodically", "regularly"
#        * User ne kaha: "schedule", "cron", "interval"
#        → KISI BHI TIME-BASED ya RECURRING task ke liye = SCHEDULE TRIGGER
     
#       WEBHOOK TRIGGER — IN CASES MEIN USE KARO:
#        * User ne kaha: "when webhook received", "on HTTP event"
#        * User ne kaha: "when someone submits", "on API call"
     
#       MANUAL TRIGGER — SIRF TAB use karo jab:
#        * Koi time/schedule/interval mention NAHI hai
#        * Koi webhook/HTTP event mention NAHI hai
#        * User clearly ek one-time task describe kar raha hai
     
#       GALTI MAT KARO: "every hour" ya "every day" ke liye MANUAL trigger kabhi mat lena — yeh SCHEDULE TRIGGER hai, ALWAYS.
# 2. Trigger ke baad hi actions add karo — trigger ke bina workflow invalid hai.
# 3. search_nodes call karo agar exact node name pata nahi.
# 4. add_node mein EXACT names use karo available list se.
# 5. connect_nodes_by_name se EVERY consecutive pair connect karo.
# 6. validate_workflow ONCE call karo end mein — pass hone ke baad STOP.
# 7. Parameters pure JSON — no // comments, no trailing commas.
# 8. Conditional node selection rule (VERY IMPORTANT):
#    - Use IF only when there is exactly ONE boolean decision with exactly 2 outcomes:
#      yes/no, true/false, exists/doesn't exist, success/failure.
#    - Use SWITCH whenever branching is based on MULTIPLE distinct conditions or multiple named outcomes.
#    - Use SWITCH for 3 or more branches — always.
#    - Also use SWITCH for 2 branches if those 2 branches are two different explicit conditions instead of a simple true/false split.
#    - Simple test:
#      * "if condition is true do A, else do B" -> IF
#      * "if status = approved do A, if status = rejected do B" -> SWITCH
#      * "if priority = high do A, if priority = low do B" -> SWITCH
#      * "if score > 80 do A, else do B" -> IF
#      * "if score > 80 do A, if score between 50 and 80 do B, if score < 50 do C" -> SWITCH
# 9. Never choose IF when the user describes separate cases like "approved/rejected", "high/low", "email/sms", or any value matching/routing logic.

# EXECUTION ORDER (strict):
#   Step 1 → add_node: TRIGGER FIRST (mandatory)
#   Step 2 → add_node: remaining action/conditional nodes
#   Step 3 → connect_nodes_by_name: har pair ko connect karo (A→B, B→C ...)
#   Step 4 → validate_workflow: ONCE, then STOP

# TRIGGER SELECTION GUIDE (STRICT — NO EXCEPTIONS):
#   Time/interval/schedule words detected? (every, daily, hourly, at X time, etc.)
#     → ALWAYS = SCHEDULE TRIGGER  (NEVER use MANUAL for these)
  
#   Webhook/HTTP event words detected?
#     → ALWAYS = WEBHOOK TRIGGER 
  
#   No time, no webhook, simple one-time task?
#     → MANUAL trigger 
  
#     "every hour", "every day", "daily", "hourly" = SCHEDULE TRIGGER — YEH RULE BREAK NAHI HOGA
# User request: {user_input}"""

#         messages = [
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=f"Build the workflow now: {user_input}"),
#         ]

#         # ── Agentic loop ──────────────────────────────────────────
#         # Hard limit: max 12 iterations (was 20 — each LLM call ~3-5s)
#         # A simple 4-node workflow needs ~8 tool calls, well within 12.
#         MAX_ITER = 12

#         done = False
#         for iteration in range(MAX_ITER):
#             try:
#                 response = await self.llm_with_tools.ainvoke(messages)
#             except Exception as e:
#                 err = str(e)
#                 if 'tool calling' in err.lower() and 'not supported' in err.lower():
#                     raise RuntimeError(
#                         "Model does not support tool calling. "
#                         "Set LLM_MODEL=llama-3.3-70b-versatile in .env"
#                     ) from e
#                 if 'Failed to parse tool call' in err or 'tool_use_failed' in err:
#                     messages.append(HumanMessage(
#                         content="JSON parse error: remove all // comments and trailing commas from parameters, then retry."
#                     ))
#                     continue
#                 raise

#             response = sanitize_tool_calls(response)
#             messages.append(response)

#             tool_calls = getattr(response, "tool_calls", None)
#             if not tool_calls:
#                 # LLM finished naturally — no more tool calls
#                 break

#             for tc in tool_calls:
#                 result = await self._execute_tool(tc["name"], tc["args"])
#                 short  = str(result)[:120]
#                 print(f"   🔧 {tc['name']}({list(tc['args'].keys())}) → {short}")
#                 messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

#                 # ── Early exit after successful validation ────────
#                 # KEY FIX: Once validate_workflow passes, we are done.
#                 # Without this the LLM keeps calling get_node_details
#                 # in a loop trying to "fix" the workflow, burning 20+ iterations.
#                 if tc["name"] == "validate_workflow" and "✅" in str(result):
#                     print(f"   ✅ Validation passed — stopping builder loop")
#                     done = True
#                     break

#             if done:
#                 break

#         # ── Safety net: auto-connect if LLM forgot ────────────────
#         connection_count = sum(
#             len(arr[0]) if arr else 0
#             for conns in workflow.connections.values()
#             for arr in conns.values()
#         )

#         if connection_count == 0 and len(workflow.nodes) > 1:
#             print("   ⚠️  No connections — auto-linking nodes in sequence")
#             from ..types.workflow import WorkflowConnection
#             for i in range(len(workflow.nodes) - 1):
#                 src, tgt = workflow.nodes[i], workflow.nodes[i + 1]
#                 workflow.connections.setdefault(src.name, {}).setdefault("main", [[]])
#                 workflow.connections[src.name]["main"][0].append(
#                     WorkflowConnection(node=tgt.name, type="main", index=0)
#                 )
#                 print(f"   🔗 Auto-linked: '{src.name}' → '{tgt.name}'")

#         connection_count = sum(
#             len(arr[0]) if arr else 0
#             for conns in workflow.connections.values()
#             for arr in conns.values()
#         )

#         print(f"   → {len(workflow.nodes)} nodes, {connection_count} connections, {iteration+1} iterations used")

#         return {
#             "summary": f"Built workflow with {len(workflow.nodes)} nodes and {connection_count} connections",
#             "nodes_added": len(workflow.nodes),
#         }

#     async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
#         t = self._tool_map.get(tool_name)
#         if not t:
#             return f"Tool '{tool_name}' not found. Available: {list(self._tool_map.keys())}"
#         try:
#             result = await t.ainvoke(tool_args) if hasattr(t, "ainvoke") else t.invoke(tool_args)
#             return str(result)
#         except Exception as e:
#             return f"Tool error ({tool_name}): {e}"

#     def _extract_last_user_message(self, state: Dict[str, Any]) -> str:
#         messages = state.get("messages", [])
#         if not messages:
#             return "Build the workflow"
#         last = messages[-1]
#         if isinstance(last, dict):
#             return last.get("content") or last.get("text") or "Build the workflow"
#         return getattr(last, "content", None) or str(last)

#     def _extract_techniques(self, state: Dict[str, Any]) -> list:
#         cat = state.get("categorization")
#         if cat is None: return []
#         if hasattr(cat, "techniques"): return getattr(cat, "techniques") or []
#         if isinstance(cat, dict): return cat.get("techniques", []) or []
#         return []





# backend/agents/builder.py
#
# CHANGE: system_prompt se "role" instruction completely hata diya.
# add_node ab sirf (node_type, name, parameters) leta hai.
# Role registry se auto-infer hota hai — LLM is decision se bahar hai.

import re
import json
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import List, Any, Dict
from backend.prompt.agents.builder_prompt import get_builder_prompt
from ..utils.config import Config


def strip_json_comments(text: str) -> str:
    result = []
    i, n, in_string = 0, len(text), False
    while i < n:
        c = text[i]
        if c == '"' and (i == 0 or text[i - 1] != '\\'):
            in_string = not in_string
            result.append(c); i += 1; continue
        if in_string:
            result.append(c); i += 1; continue
        if c == '/' and i + 1 < n:
            if text[i + 1] == '/':
                while i < n and text[i] != '\n': i += 1
                continue
            if text[i + 1] == '*':
                i += 2
                while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'): i += 1
                i += 2; continue
        result.append(c); i += 1
    cleaned = ''.join(result)
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    return cleaned.strip()


def sanitize_tool_calls(response: AIMessage) -> AIMessage:
    if not getattr(response, 'tool_calls', None):
        return response
    fixed = []
    for tc in response.tool_calls:
        args = tc.get('args', {})
        if isinstance(args, str):
            try:
                args = json.loads(strip_json_comments(args))
            except:
                args = {}
        if isinstance(args, dict):
            try:
                args = json.loads(strip_json_comments(json.dumps(args)))
            except:
                pass
        fixed.append({**tc, 'args': args})
    response.tool_calls = fixed
    return response


class BuilderAgent:

    def __init__(self, llm: BaseChatModel, tools: List[Any], search_engine):
        self.llm = llm
        self.tools = tools
        self.search_engine = search_engine
        self.llm_with_tools = llm.bind_tools(tools) if tools else llm
        self._tool_map = {t.name: t for t in tools}

    async def build_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        workflow   = state["workflow_json"]
        # Guard: if workflow already has nodes, builder already ran — skip
        if workflow.nodes:
            return {
                "summary": f"Workflow already built with {len(workflow.nodes)} nodes — skipping",
                "nodes_added": len(workflow.nodes),
            }
        user_input = self._extract_last_user_message(state)

        all_nodes = self.search_engine.get_all_node_names()
        triggers  = [n for n in all_nodes if n["nodeType"] == "trigger"]
        actions   = [n for n in all_nodes if n["nodeType"] == "action"]
        conds     = [n for n in all_nodes if n["nodeType"] == "conditional"]

        def fmt(lst):
            return ", ".join(n["name"] for n in lst)
        
        
#         system_prompt = f"""You are a workflow builder. Build a complete workflow for the user's request.

# AVAILABLE NODES
#   Triggers    (start the workflow): {fmt(triggers)}
#   Actions     (do something):       {fmt(actions)}
#   Conditionals (branch the flow):   {fmt(conds)}

# RULES — follow exactly:
# 1. FIRST node MUST always be a Trigger — pick from the Triggers list above.

#    TRIGGER SELECTION (strict, check in order):
#    - Time/interval/schedule words → SCHEDULE TRIGGER (every hour, daily, at 9am, etc.)
#    - Webhook/HTTP event words     → WEBHOOK
#    - External service has its own trigger (e.g. TYPEFORM, GITHUB) → use that service trigger
#    - No time, no event, one-time  → MANUAL

# 2. add_node takes ONLY: node_type, name, parameters.
#    Do NOT pass a 'role' field — it is set automatically by the system.

# 3. node_type MUST be an exact name from the lists above.
#    Call search_nodes first if unsure.

# 4. connect_nodes_by_name for EVERY consecutive pair of nodes.

# 5. validate_workflow ONCE at the end — stop after it passes.

# 6. Parameters: pure JSON — no // comments, no trailing commas.

# 7. Conditional selection:
#    - IF   → exactly one boolean split (true/false, yes/no)
#    - SWITCH → 1+ branches, OR 2 named conditions (approved/rejected, high/low)
#    - Never use IF for non-boolean splits.
#    - Always use SWITCH for 3+ branches.
#    - For 2 branches, use IF only if it's a simple true/false split. If it's two distinct conditions, use SWITCH.

# EXECUTION ORDER:
#   Step 1 → add_node: TRIGGER first (mandatory)
#   Step 2 → add_node: remaining nodes
#   Step 3 → connect_nodes_by_name: every consecutive pair
#   Step 4 → validate_workflow: once, then STOP

# User request: {user_input}"""

        base_prompt = get_builder_prompt()
        messages = [
            SystemMessage(content=base_prompt),
            HumanMessage(content=f"""Build the workflow now: 
                         AVAILABLE NODES:
                            Triggers: {fmt(triggers)}
                            Actions: {fmt(actions)}
                            Conditionals: {fmt(conds)}
                        {user_input}"""),
        ]

        MAX_ITER = Config.MAX_ITERATIONS
        done = False

        for iteration in range(MAX_ITER):
            try:
                response = await self.llm_with_tools.ainvoke(messages)
            except Exception as e:
                err = str(e)
                if 'tool calling' in err.lower() and 'not supported' in err.lower():
                    raise RuntimeError(
                        "Model does not support tool calling. "
                        "Set LLM_MODEL=llama-3.3-70b-versatile in .env"
                    ) from e
                if 'Failed to parse tool call' in err or 'tool_use_failed' in err:
                    messages.append(HumanMessage(
                        content="JSON parse error: remove all // comments and trailing commas, then retry."
                    ))
                    continue
                raise

            response = sanitize_tool_calls(response)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                break

            for tc in tool_calls:
                # Safety: strip 'role' if LLM still passes it despite instructions
                args = tc.get("args", {})
                if isinstance(args, dict):
                    args.pop("role", None)
                    tc = {**tc, "args": args}

                result = await self._execute_tool(tc["name"], tc["args"])
                short  = str(result)[:120]
                print(f"   tool: {tc['name']}({list(tc['args'].keys())}) → {short}")
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

                if tc["name"] == "validate_workflow" and ("-->>>" in str(result) or "-->>" in str(result) or "Validation passed" in str(result)):
                    print("   -->> Validation passed — stopping builder loop")
                    done = True
                    break

            if done:
                break

        # Safety net: auto-connect if LLM forgot
        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )

        if connection_count == 0 and len(workflow.nodes) > 1:
            print("   No connections — auto-linking nodes in sequence")
            from ..types.workflow import WorkflowConnection
            for i in range(len(workflow.nodes) - 1):
                src, tgt = workflow.nodes[i], workflow.nodes[i + 1]
                workflow.connections.setdefault(src.name, {}).setdefault("main", [[]])
                workflow.connections[src.name]["main"][0].append(
                    WorkflowConnection(node=tgt.name, type="main", index=0)
                )

        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )

        print(f"   {len(workflow.nodes)} nodes, {connection_count} connections, {iteration+1} iterations")

        return {
            "summary": f"Built workflow with {len(workflow.nodes)} nodes and {connection_count} connections",
            "nodes_added": len(workflow.nodes),
        }

    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        t = self._tool_map.get(tool_name)
        if not t:
            return f"Tool '{tool_name}' not found. Available: {list(self._tool_map.keys())}"
        try:
            result = await t.ainvoke(tool_args) if hasattr(t, "ainvoke") else t.invoke(tool_args)
            return str(result)
        except Exception as e:
            return f"Tool error ({tool_name}): {e}"

    def _extract_last_user_message(self, state: Dict[str, Any]) -> str:
        messages = state.get("messages", [])
        if not messages:
            return "Build the workflow"
        last = messages[-1]
        if isinstance(last, dict):
            return last.get("content") or last.get("text") or "Build the workflow"
        return getattr(last, "content", None) or str(last)

    def _extract_techniques(self, state: Dict[str, Any]) -> list:
        cat = state.get("categorization")
        if cat is None:
            return []
        if hasattr(cat, "techniques"):
            return getattr(cat, "techniques") or []
        if isinstance(cat, dict):
            return cat.get("techniques", []) or []
        return []