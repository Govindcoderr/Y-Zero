
# agents/builder.py
import re
import json
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import List, Any, Dict

#
# JSON comment/trailing-comma stripper#
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
            try: args = json.loads(strip_json_comments(args))
            except: args = {}
        if isinstance(args, dict):
            try: args = json.loads(strip_json_comments(json.dumps(args)))
            except: pass
        fixed.append({**tc, 'args': args})
    response.tool_calls = fixed
    return response

#
# BuilderAgent#
class BuilderAgent:

    def __init__(self, llm: BaseChatModel, tools: List[Any], search_engine):
        self.llm = llm
        self.tools = tools
        self.search_engine = search_engine
        self.llm_with_tools = llm.bind_tools(tools) if tools else llm
        # Build a quick tool lookup map
        self._tool_map = {t.name: t for t in tools}

    async def build_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        workflow   = state["workflow_json"]
        user_input = self._extract_last_user_message(state)

        # ── Build compact node catalogue for prompt ───────────────
        all_nodes  = self.search_engine.get_all_node_names()
        triggers   = [n for n in all_nodes if n["nodeType"] == "trigger"]
        actions    = [n for n in all_nodes if n["nodeType"] == "action"]
        conds      = [n for n in all_nodes if n["nodeType"] == "conditional"]

        def fmt(lst): return ", ".join(n["name"] for n in lst)

        system_prompt = f"""You are a workflow builder. Build a complete workflow for the user's request.

AVAILABLE NODES
  Triggers    (start the workflow): {fmt(triggers)}
  Actions     (do something):       {fmt(actions)}
  Conditionals (branch the flow):   {fmt(conds)}

RULES — follow exactly, no exceptions:
1. First call search_nodes if you are unsure which node to use.
2. Add nodes with add_node using EXACT names from the list above.
3. Connect EVERY consecutive node with connect_nodes_by_name.
4. Call validate_workflow ONCE at the end.
5. Stop after validate_workflow — do NOT call get_node_details in a loop.
6. Parameters must be pure JSON — no // comments, no trailing commas.
7. A workflow MUST start with a Trigger node.

EXECUTION ORDER:
  Step 1 → add_node  (trigger first, then actions/conditionals in order)
  Step 2 → connect_nodes_by_name  (link every pair: A→B, B→C, C→D …)
  Step 3 → validate_workflow  (ONCE — then stop)

User request: {user_input}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Build the workflow now: {user_input}"),
        ]

        # ── Agentic loop ──────────────────────────────────────────
        # Hard limit: max 12 iterations (was 20 — each LLM call ~3-5s)
        # A simple 4-node workflow needs ~8 tool calls, well within 12.
        MAX_ITER = 12

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
                        content="JSON parse error: remove all // comments and trailing commas from parameters, then retry."
                    ))
                    continue
                raise

            response = sanitize_tool_calls(response)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                # LLM finished naturally — no more tool calls
                break

            for tc in tool_calls:
                result = await self._execute_tool(tc["name"], tc["args"])
                short  = str(result)[:120]
                print(f"   🔧 {tc['name']}({list(tc['args'].keys())}) → {short}")
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

                # ── Early exit after successful validation ────────
                # KEY FIX: Once validate_workflow passes, we are done.
                # Without this the LLM keeps calling get_node_details
                # in a loop trying to "fix" the workflow, burning 20+ iterations.
                if tc["name"] == "validate_workflow" and "✅" in str(result):
                    print(f"   ✅ Validation passed — stopping builder loop")
                    done = True
                    break

            if done:
                break

        # ── Safety net: auto-connect if LLM forgot ────────────────
        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )

        if connection_count == 0 and len(workflow.nodes) > 1:
            print("   ⚠️  No connections — auto-linking nodes in sequence")
            from ..types.workflow import WorkflowConnection
            for i in range(len(workflow.nodes) - 1):
                src, tgt = workflow.nodes[i], workflow.nodes[i + 1]
                workflow.connections.setdefault(src.name, {}).setdefault("main", [[]])
                workflow.connections[src.name]["main"][0].append(
                    WorkflowConnection(node=tgt.name, type="main", index=0)
                )
                print(f"   🔗 Auto-linked: '{src.name}' → '{tgt.name}'")

        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )

        print(f"   → {len(workflow.nodes)} nodes, {connection_count} connections, {iteration+1} iterations used")

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
        if cat is None: return []
        if hasattr(cat, "techniques"): return getattr(cat, "techniques") or []
        if isinstance(cat, dict): return cat.get("techniques", []) or []
        return []