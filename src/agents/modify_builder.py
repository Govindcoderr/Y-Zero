import json
import re
from typing import Any, Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from src.prompt.agents.modify_builder_prompt import get_modify_builder_prompt

from ..utils.config import Config


def strip_json_comments(text: str) -> str:
    result = []
    i, n, in_string = 0, len(text), False
    while i < n:
        c = text[i]
        if c == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        if in_string:
            result.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n:
            if text[i + 1] == "/":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            if text[i + 1] == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue
        result.append(c)
        i += 1
    cleaned = "".join(result)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned.strip()


def sanitize_tool_calls(response: AIMessage) -> AIMessage:
    if not getattr(response, "tool_calls", None):
        return response
    fixed = []
    for tc in response.tool_calls:
        args = tc.get("args", {})
        if isinstance(args, str):
            try:
                args = json.loads(strip_json_comments(args))
            except Exception:
                args = {}
        if isinstance(args, dict):
            try:
                args = json.loads(strip_json_comments(json.dumps(args)))
            except Exception:
                pass
        fixed.append({**tc, "args": args})
    response.tool_calls = fixed
    return response


class ModifyWorkflowAgent:
    def __init__(self, llm: BaseChatModel, tools: List[Any], search_engine):
        self.llm = llm
        self.tools = tools
        self.search_engine = search_engine
        self.llm_with_tools = llm.bind_tools(tools) if tools else llm
        self._tool_map = {t.name: t for t in tools}

    async def build_or_modify_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
        workflow = state["workflow_json"]
        user_input = self._extract_last_user_message(state)
        is_modification = bool(workflow.nodes) and state.get("greeter_intent") == "WORKFLOW_MODIFY"

        all_nodes = self.search_engine.get_all_node_names()
        triggers = [n for n in all_nodes if n["nodeType"] == "trigger"]
        actions = [n for n in all_nodes if n["nodeType"] == "action"]
        conds = [n for n in all_nodes if n["nodeType"] == "conditional"]

        def fmt(lst):
            return ", ".join(n["name"] for n in lst)

        current_workflow_summary = ""
        if workflow.nodes:
            current_workflow_summary = (
                "CURRENT WORKFLOW:\n"
                + "\n".join(
                    f"- {node.name} ({node.type}) params={json.dumps(node.parameters, ensure_ascii=True)}"
                    for node in workflow.nodes
                )
                + "\nCURRENT CONNECTIONS:\n"
                + json.dumps(workflow.to_dict().get("connections", {}), ensure_ascii=True)
            )

        messages = [
            SystemMessage(content=get_modify_builder_prompt()),
            HumanMessage(content=f"""MODE: {"MODIFY_EXISTING_WORKFLOW" if is_modification else "BUILD_NEW_WORKFLOW"}
AVAILABLE NODES:
Triggers: {fmt(triggers)}
Actions: {fmt(actions)}
Conditionals: {fmt(conds)}

{current_workflow_summary}

USER REQUEST:
{user_input}"""),
        ]

        max_iter = Config.MAX_ITERATIONS
        done = False
        

        for iteration in range(max_iter):
            response = await self.llm_with_tools.ainvoke(messages)
            response = sanitize_tool_calls(response)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                break

            for tc in tool_calls:
                args = tc.get("args", {})
                if isinstance(args, dict):
                    args.pop("role", None)
                    tc = {**tc, "args": args}

                result = await self._execute_tool(tc["name"], tc["args"])
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

                if tc["name"] == "validate_workflow" and (
                    "-->>>" in str(result) or "-->>" in str(result) or "Validation passed" in str(result)
                ):
                    done = True
                    break

            if done:
                break

        connection_count = sum(
            len(arr[0]) if arr else 0
            for conns in workflow.connections.values()
            for arr in conns.values()
        )

        summary = (
            f"Modified workflow with {len(workflow.nodes)} nodes and {connection_count} connections"
            if is_modification
            else f"Built workflow with {len(workflow.nodes)} nodes and {connection_count} connections"
        )
        return {"summary": summary, "nodes_added": len(workflow.nodes)}

    async def _execute_tool(self, tool_name: str, tool_args: Dict) -> str:
        tool_impl = self._tool_map.get(tool_name)
        if not tool_impl:
            return f"Tool '{tool_name}' not found. Available: {list(self._tool_map.keys())}"
        try:
            result = await tool_impl.ainvoke(tool_args) if hasattr(tool_impl, "ainvoke") else tool_impl.invoke(tool_args)
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
