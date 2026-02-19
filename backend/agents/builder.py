

# # agents/builder.py
# from langchain_core.language_models import BaseChatModel
# from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
# from typing import List, Any, Dict


# class BuilderAgent:
#     """Agent responsible for building workflow structure using tools"""

#     def __init__(self, llm: BaseChatModel, tools: List[Any], search_engine):
#         self.llm = llm
#         self.tools = tools
#         self.search_engine = search_engine
#         self.llm_with_tools = llm.bind_tools(tools) if tools else llm

#     async def build_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         """Build workflow by adding and connecting nodes via tool calls"""

#         workflow = state["workflow_json"]
#         user_input = self._extract_last_user_message(state)
#         techniques = self._extract_techniques(state)
#         best_practices = state.get("best_practices", "")
#         available_nodes = self._get_available_nodes(state)

#         system_prompt = f"""You are an expert n8n workflow builder. Build a complete workflow using the tools provided.

# User request: {user_input}

# Identified techniques: {', '.join([t.value if hasattr(t, 'value') else str(t) for t in techniques])}

# Best practices:
# {best_practices}

# Available node types:
# {available_nodes}

# == CRITICAL INSTRUCTIONS ==

# STEP 1 - ADD ALL NODES using add_node:
#   - Add a trigger node first (scheduleTrigger, webhook, etc.)
#   - Add all processing/action nodes in execution order
#   - Each call to add_node returns the node's UUID - remember it!

# STEP 2 - CONNECT ALL NODES using connect_nodes_by_name:
#   - After adding ALL nodes, connect every consecutive pair
#   - You MUST call connect_nodes_by_name for EVERY link in the chain
#   - If you have nodes A → B → C → D, make 3 connect calls:
#       connect_nodes_by_name("A", "B")
#       connect_nodes_by_name("B", "C")  
#       connect_nodes_by_name("C", "D")
#   - Use the EXACT node names you passed to add_node
#   - 0 connections = broken workflow, always connect!

# STEP 3 - VERIFY with validate_workflow

# Do not skip any step. A workflow with 0 connections is incomplete."""

#         messages = [
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=f"Build a complete, connected workflow for: {user_input}"),
#         ]

#         max_iterations = 20
#         iteration = 0

#         while iteration < max_iterations:
#             iteration += 1
#             response = await self.llm_with_tools.ainvoke(messages)
#             messages.append(response)

#             tool_calls = getattr(response, "tool_calls", None)
#             if not tool_calls:
#                 break

#             for tool_call in tool_calls:
#                 tool_name = tool_call["name"]
#                 tool_args = tool_call["args"]
#                 tool_id = tool_call["id"]

#                 tool_result = await self._execute_tool(tool_name, tool_args)
#                 print(f"   🔧 {tool_name}({tool_args}) → {tool_result[:80]}")

#                 messages.append(
#                     ToolMessage(content=str(tool_result), tool_call_id=tool_id)
#                 )

#         # Count actual connections
#         connection_count = sum(
#             len(arr[0]) if arr else 0
#             for conns in workflow.connections.values()
#             for arr in conns.values()
#         )

#         # If LLM forgot to connect, auto-connect nodes in order
#         if connection_count == 0 and len(workflow.nodes) > 1:
#             print("   ⚠️  No connections made by LLM - auto-connecting nodes in sequence")
#             for i in range(len(workflow.nodes) - 1):
#                 src = workflow.nodes[i]
#                 tgt = workflow.nodes[i + 1]

#                 if src.name not in workflow.connections:
#                     workflow.connections[src.name] = {}
#                 if "main" not in workflow.connections[src.name]:
#                     workflow.connections[src.name]["main"] = [[]]

#                 from ..types.workflow import WorkflowConnection
#                 workflow.connections[src.name]["main"][0].append(
#                     WorkflowConnection(node=tgt.name, type="main", index=0)
#                 )
#                 print(f"   🔗 Auto-linked: '{src.name}' → '{tgt.name}'")

#         connection_count = sum(
#             len(arr[0]) if arr else 0
#             for conns in workflow.connections.values()
#             for arr in conns.values()
#         )

#         final_content = ""
#         for msg in reversed(messages):
#             if isinstance(msg, AIMessage) and msg.content:
#                 final_content = msg.content if isinstance(msg.content, str) else str(msg.content)
#                 break

#         return {
#             "summary": final_content or f"Built workflow with {len(workflow.nodes)} nodes and {connection_count} connections",
#             "nodes_added": len(workflow.nodes),
#         }

#     async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
#         for t in self.tools:
#             if t.name == tool_name:
#                 try:
#                     if hasattr(t, "ainvoke"):
#                         result = await t.ainvoke(tool_args)
#                     else:
#                         result = t.invoke(tool_args)
#                     return str(result)
#                 except Exception as e:
#                     return f"Tool error ({tool_name}): {e}"
#         return f"Tool '{tool_name}' not found. Available: {[t.name for t in self.tools]}"

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
#         if cat is None:
#             return []
#         if hasattr(cat, "techniques"):
#             return getattr(cat, "techniques") or []
#         if isinstance(cat, dict):
#             return cat.get("techniques", []) or []
#         return []

#     def _get_available_nodes(self, state: Dict[str, Any]) -> str:
#         nodes = state.get("available_node_types", [])
#         if not nodes:
#             nodes = self.search_engine.node_types
#         lines = []
#         for n in nodes[:20]:
#             lines.append(f"  - {n.get('name')}: {n.get('displayName')} — {n.get('description', '')}")
#         return "\n".join(lines)




# # agents/builder.py
# from langchain_core.language_models import BaseChatModel
# from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
# from typing import List, Any, Dict


# class BuilderAgent:
#     """Agent responsible for building workflow structure using tools"""

#     def __init__(self, llm: BaseChatModel, tools: List[Any], search_engine):
#         self.llm = llm
#         self.tools = tools
#         self.search_engine = search_engine
#         self.llm_with_tools = llm.bind_tools(tools) if tools else llm

#     async def build_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
#         """Build workflow by adding and connecting nodes via tool calls"""

#         workflow = state["workflow_json"]
#         user_input = self._extract_last_user_message(state)
#         techniques = self._extract_techniques(state)
#         best_practices = state.get("best_practices", "")
#         available_nodes = self._get_available_nodes(state)

#         system_prompt = f"""You are an expert n8n workflow builder. Build a complete workflow using the tools provided.

# User request: {user_input}

# Identified techniques: {', '.join([t.value if hasattr(t, 'value') else str(t) for t in techniques])}

# Best practices:
# {best_practices}

# Available node types:
# {available_nodes}

# == CRITICAL INSTRUCTIONS ==

# STEP 1 - ADD ALL NODES using add_node:
#   - Add a trigger node first (scheduleTrigger, webhook, etc.)
#   - Add all processing/action nodes in execution order
#   - Each call to add_node returns the node's UUID - remember it!

# STEP 2 - CONNECT ALL NODES using connect_nodes_by_name:
#   - After adding ALL nodes, connect every consecutive pair
#   - You MUST call connect_nodes_by_name for EVERY link in the chain
#   - If you have nodes A → B → C → D, make 3 connect calls:
#       connect_nodes_by_name("A", "B")
#       connect_nodes_by_name("B", "C")  
#       connect_nodes_by_name("C", "D")
#   - Use the EXACT node names you passed to add_node
#   - 0 connections = broken workflow, always connect!

# STEP 3 - OPTIONALLY call validate_workflow to verify everything is correct.

# Do not skip steps 1 and 2. A workflow with 0 connections is incomplete."""

#         messages = [
#             SystemMessage(content=system_prompt),
#             HumanMessage(content=f"Build a complete, connected workflow for: {user_input}"),
#         ]

#         max_iterations = 20
#         iteration = 0

#         while iteration < max_iterations:
#             iteration += 1
#             response = await self.llm_with_tools.ainvoke(messages)
#             messages.append(response)

#             tool_calls = getattr(response, "tool_calls", None)
#             if not tool_calls:
#                 break

#             for tool_call in tool_calls:
#                 tool_name = tool_call["name"]
#                 tool_args = tool_call["args"]
#                 tool_id = tool_call["id"]

#                 tool_result = await self._execute_tool(tool_name, tool_args)
#                 print(f"   🔧 {tool_name}({tool_args}) → {tool_result[:80]}")

#                 messages.append(
#                     ToolMessage(content=str(tool_result), tool_call_id=tool_id)
#                 )

#         # Count actual connections
#         connection_count = sum(
#             len(arr[0]) if arr else 0
#             for conns in workflow.connections.values()
#             for arr in conns.values()
#         )

#         # If LLM forgot to connect, auto-connect nodes in order
#         if connection_count == 0 and len(workflow.nodes) > 1:
#             print("   ⚠️  No connections made by LLM - auto-connecting nodes in sequence")
#             for i in range(len(workflow.nodes) - 1):
#                 src = workflow.nodes[i]
#                 tgt = workflow.nodes[i + 1]

#                 if src.name not in workflow.connections:
#                     workflow.connections[src.name] = {}
#                 if "main" not in workflow.connections[src.name]:
#                     workflow.connections[src.name]["main"] = [[]]

#                 from ..types.workflow import WorkflowConnection
#                 workflow.connections[src.name]["main"][0].append(
#                     WorkflowConnection(node=tgt.name, type="main", index=0)
#                 )
#                 print(f"   🔗 Auto-linked: '{src.name}' → '{tgt.name}'")

#         connection_count = sum(
#             len(arr[0]) if arr else 0
#             for conns in workflow.connections.values()
#             for arr in conns.values()
#         )

#         final_content = ""
#         for msg in reversed(messages):
#             if isinstance(msg, AIMessage) and msg.content:
#                 final_content = msg.content if isinstance(msg.content, str) else str(msg.content)
#                 break

#         return {
#             "summary": final_content or f"Built workflow with {len(workflow.nodes)} nodes and {connection_count} connections",
#             "nodes_added": len(workflow.nodes),
#         }

#     async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
#         for t in self.tools:
#             if t.name == tool_name:
#                 try:
#                     if hasattr(t, "ainvoke"):
#                         result = await t.ainvoke(tool_args)
#                     else:
#                         result = t.invoke(tool_args)
#                     return str(result)
#                 except Exception as e:
#                     return f"Tool error ({tool_name}): {e}"
#         return f"Tool '{tool_name}' not found. Available: {[t.name for t in self.tools]}"

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
#         if cat is None:
#             return []
#         if hasattr(cat, "techniques"):
#             return getattr(cat, "techniques") or []
#         if isinstance(cat, dict):
#             return cat.get("techniques", []) or []
#         return []

#     def _get_available_nodes(self, state: Dict[str, Any]) -> str:
#         nodes = state.get("available_node_types", [])
#         if not nodes:
#             nodes = self.search_engine.node_types
#         lines = []
#         for n in nodes[:20]:
#             lines.append(f"  - {n.get('name')}: {n.get('displayName')} — {n.get('description', '')}")
#         return "\n".join(lines)
# agents/builder.py
import re
import json
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import List, Any, Dict


def strip_json_comments(text: str) -> str:
    """
    Remove JS-style // and /* */ comments from a JSON string.
    Uses a state machine so it never touches content inside quoted strings.
    Also removes trailing commas before } or ] which break json.loads.
    """
    result = []
    i = 0
    in_string = False
    n = len(text)

    while i < n:
        c = text[i]
        if c == '"' and (i == 0 or text[i - 1] != '\\'):
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        if in_string:
            result.append(c)
            i += 1
            continue
        if c == '/' and i + 1 < n:
            if text[i + 1] == '/':
                while i < n and text[i] != '\n':
                    i += 1
                continue
            if text[i + 1] == '*':
                i += 2
                while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                    i += 1
                i += 2
                continue
        result.append(c)
        i += 1

    import re as _re
    cleaned = ''.join(result)
    cleaned = _re.sub(r',\s*([}\]])', r'\1', cleaned)
    return cleaned.strip()



def sanitize_tool_calls(response: AIMessage) -> AIMessage:
    """
    Fix LLM tool call arguments that contain JS-style comments or trailing commas.
    Mutates tool_calls in-place and returns the message.
    """
    if not hasattr(response, 'tool_calls') or not response.tool_calls:
        return response

    fixed_calls = []
    for tc in response.tool_calls:
        args = tc.get('args', {})

        # If args came through as a raw string (some versions), parse it
        if isinstance(args, str):
            try:
                cleaned = strip_json_comments(args)
                args = json.loads(cleaned)
            except Exception:
                args = {}

        # If args is already a dict, check each string value for embedded JSON comments
        # (this handles the case where langchain already parsed but left junk)
        if isinstance(args, dict):
            # Re-serialize and re-parse to catch any issues
            try:
                raw = json.dumps(args)
                cleaned = strip_json_comments(raw)
                args = json.loads(cleaned)
            except Exception:
                pass  # keep original args if cleaning fails

        fixed_calls.append({**tc, 'args': args})

    # Rebuild the message with fixed tool calls
    response.tool_calls = fixed_calls
    return response


class BuilderAgent:
    """Agent responsible for building workflow structure using tools"""

    def __init__(self, llm: BaseChatModel, tools: List[Any], search_engine):
        self.llm = llm
        self.tools = tools
        self.search_engine = search_engine
        self.llm_with_tools = llm.bind_tools(tools) if tools else llm

    async def build_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Build workflow by adding and connecting nodes via tool calls"""

        workflow = state["workflow_json"]
        user_input = self._extract_last_user_message(state)
        techniques = self._extract_techniques(state)
        best_practices = state.get("best_practices", "")
        available_nodes = self._get_available_nodes(state)

        system_prompt = f"""You are an expert n8n workflow builder. Build a complete workflow using the tools provided.

User request: {user_input}

Identified techniques: {', '.join([t.value if hasattr(t, 'value') else str(t) for t in techniques])}

Best practices:
{best_practices}

Available node types:
{available_nodes}

== CRITICAL INSTRUCTIONS ==

STEP 0 - RESOLVE NODE TYPES using resolve_node_type:
  - Before adding ANY node, call resolve_node_type with the type you intend to use.
  - ONLY the exact node types returned by this tool exist in the system.
  - If the node you want (e.g. 'workflow.whatsapp', 'workflow.telegram') is not
    available, resolve_node_type will tell you the best alternative to use instead.
  - Example: resolve_node_type("workflow.whatsapp") might return "workflow.httpRequest"
    with instructions to use Twilio/WhatsApp API via HTTP.
  - Do NOT invent node type names. Only use what resolve_node_type confirms.

STEP 1 - ADD ALL NODES using add_node:
  - Add a trigger node first (use resolved type from step 0)
  - Add all processing/action nodes in execution order
  - Use only the node_type values confirmed by resolve_node_type
  - IMPORTANT: parameters must be valid JSON — NO comments (no // or /* */), NO trailing commas

STEP 2 - CONNECT ALL NODES using connect_nodes_by_name:
  - After adding ALL nodes, connect every consecutive pair
  - You MUST call connect_nodes_by_name for EVERY link in the chain
  - If you have nodes A → B → C → D, make 3 connect calls:
      connect_nodes_by_name("A", "B")
      connect_nodes_by_name("B", "C")
      connect_nodes_by_name("C", "D")
  - Use the EXACT node names you passed to add_node
  - 0 connections = broken workflow, always connect!

STEP 3 - OPTIONALLY call validate_workflow to verify everything is correct.

Do not skip steps 0, 1 and 2. Never invent node types not confirmed by resolve_node_type.
NEVER put comments in JSON parameters. Use only pure JSON values."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Build a complete, connected workflow for: {user_input}"),
        ]

        max_iterations = 20
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                response = await self.llm_with_tools.ainvoke(messages)
            except Exception as e:
                error_msg = str(e)
                # If it's a JSON parse error from commented args, inject a correction message
                if 'Failed to parse tool call' in error_msg or 'tool_use_failed' in error_msg:
                    print(f"   ⚠️  Tool call JSON parse error, injecting correction hint...")
                    messages.append(
                        HumanMessage(
                            content=(
                                "Your last tool call failed because the 'parameters' JSON "
                                "contained comments (// ...) or trailing commas. "
                                "JSON does not support comments. "
                                "Please retry with pure valid JSON — no // comments, "
                                "no /* */ comments, no trailing commas."
                            )
                        )
                    )
                    continue
                raise

            # Sanitize tool call args to strip any JS comments the LLM snuck in
            response = sanitize_tool_calls(response)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                break

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                tool_result = await self._execute_tool(tool_name, tool_args)
                short = str(tool_result)[:100]
                print(f"   🔧 {tool_name}({list(tool_args.keys())}) → {short}")

                messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tool_id)
                )

        # Count actual connections
        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )

        # Safety net: if LLM forgot to connect, auto-connect nodes in sequence
        if connection_count == 0 and len(workflow.nodes) > 1:
            print("   ⚠️  No connections made by LLM — auto-connecting nodes in sequence")
            from ..types.workflow import WorkflowConnection
            for i in range(len(workflow.nodes) - 1):
                src = workflow.nodes[i]
                tgt = workflow.nodes[i + 1]
                if src.name not in workflow.connections:
                    workflow.connections[src.name] = {}
                if "main" not in workflow.connections[src.name]:
                    workflow.connections[src.name]["main"] = [[]]
                workflow.connections[src.name]["main"][0].append(
                    WorkflowConnection(node=tgt.name, type="main", index=0)
                )
                print(f"   🔗 Auto-linked: '{src.name}' → '{tgt.name}'")

        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )

        final_content = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                break

        return {
            "summary": final_content or f"Built workflow with {len(workflow.nodes)} nodes and {connection_count} connections",
            "nodes_added": len(workflow.nodes),
        }

    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        for t in self.tools:
            if t.name == tool_name:
                try:
                    if hasattr(t, "ainvoke"):
                        result = await t.ainvoke(tool_args)
                    else:
                        result = t.invoke(tool_args)
                    return str(result)
                except Exception as e:
                    return f"Tool error ({tool_name}): {e}"
        return f"Tool '{tool_name}' not found. Available: {[t.name for t in self.tools]}"

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

    def _get_available_nodes(self, state: Dict[str, Any]) -> str:
        nodes = state.get("available_node_types", [])
        if not nodes:
            nodes = self.search_engine.node_types
        lines = []
        for n in nodes[:20]:
            lines.append(
                f"  - {n.get('name')}: {n.get('displayName')} — {n.get('description', '')}"
            )
        return "\n".join(lines)