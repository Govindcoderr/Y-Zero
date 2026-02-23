
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
    



    # types/workflow.py
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


# ------------------------------------------------------------------
# Node type → output format "type" and "value" mapping
# ------------------------------------------------------------------
# "type" is one of: trigger | action | condition | output
# "value" is the display label used in expressionExecutionName
NODE_TYPE_MAP: Dict[str, Dict[str, str]] = {
    # Triggers
    "workflow.scheduleTrigger": {"type": "trigger", "value": "SCHEDULE",    "operation": "1"},
    "workflow.webhook":         {"type": "trigger", "value": "WEBHOOK",     "operation": "1"},
    "workflow.manualTrigger":   {"type": "trigger", "value": "MANUAL",      "operation": "2"},
    # Actions / HTTP
    "workflow.httpRequest":     {"type": "action",  "value": "HTTP REQUEST", "operation": "3"},
    # Data
    "workflow.set":             {"type": "action",  "value": "SET DATA",     "operation": "3"},
    "workflow.code":            {"type": "action",  "value": "CODE",         "operation": "3"},
    # Conditions
    "workflow.if":              {"type": "condition","value": "IF",           "operation": "3"},
    # Outputs / notifications
    "workflow.emailSend":       {"type": "action",  "value": "SEND EMAIL",   "operation": "3"},
    "workflow.slack":           {"type": "action",  "value": "SLACK MESSAGE","operation": "3"},
}

# Fallback for unknown node types
_DEFAULT_NODE_META = {"type": "action", "value": "ACTION", "operation": "3"}


def _node_meta(node_type: str) -> Dict[str, str]:
    """Return output-format metadata for a given internal node type."""
    return NODE_TYPE_MAP.get(node_type, {**_DEFAULT_NODE_META, "value": node_type.split(".")[-1].upper()})


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------

@dataclass
class WorkflowNode:
    id: str
    name: str
    type: str           # internal type e.g. "workflow.httpRequest"
    type_version: int
    position: Tuple[int, int]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Internal representation (used internally by agents/tools)."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "typeVersion": self.type_version,
            "position": list(self.position),
            "parameters": self.parameters,
        }

    def to_output_dict(self) -> Dict[str, Any]:
        """
        Final API output format:
        {
            "node_key": "<uuid>",
            "nodeId":   "<uuid>",
            "type":     "trigger" | "action" | "condition" | "output",
            "value":    "HTTP REQUEST" | "SCHEDULE" | ...,
            "expressionExecutionName": "<same as value>",
            "parameters": { ... }
        }
        """
        meta = _node_meta(self.type)

        # Build enriched parameters: merge user-supplied params with defaults
        params = self._build_output_parameters(meta)

        return {
            "node_key": self.id,
            "nodeId":   self.id,
            "type":     meta["type"],
            "value":    meta["value"],
            "expressionExecutionName": meta["value"],
            "parameters": params,
        }

    def _build_output_parameters(self, meta: Dict[str, str]) -> Dict[str, Any]:
        """
        Enrich raw parameters with output-format defaults based on node type.
        Always includes 'operation'. HTTP nodes get the full parameter scaffold.
        """
        base = dict(self.parameters)  # copy

        # Always add operation
        base.setdefault("operation", meta["operation"])

        # HTTP Request node gets the full scaffold if not already present
        if self.type == "workflow.httpRequest":
            base.setdefault("method", "GET")
            base.setdefault("url", "")
            base.setdefault("sendBody", False)
            base.setdefault("sendQuery", False)
            base.setdefault("sendHeaders", False)
            base.setdefault("contentType", "json")
            base.setdefault("specifyBody", "json")
            base.setdefault("specifyQuery", "keypair")
            base.setdefault("specifyHeaders", "keypair")
            base.setdefault("authentication", "none")
            base.setdefault("bodyParameters",   {"parameters": [{}]})
            base.setdefault("queryParameters",  {"parameters": [{}]})
            base.setdefault("headerParameters", {"parameters": [{}]})

        # Schedule trigger
        if self.type == "workflow.scheduleTrigger":
            base.setdefault("rule", "0 * * * *")
            base.setdefault("timezone", "UTC")

        # Webhook
        if self.type == "workflow.webhook":
            base.setdefault("path", "/webhook")
            base.setdefault("method", "POST")

        # Email
        if self.type == "workflow.emailSend":
            base.setdefault("toEmail", "")
            base.setdefault("subject", "")
            base.setdefault("text", "")

        # Slack
        if self.type == "workflow.slack":
            base.setdefault("channel", "")
            base.setdefault("text", "")

        return base


@dataclass
class WorkflowEdge:
    """Represents a directed connection between two nodes by their IDs."""
    from_node_id: str   # source node UUID
    to_node_id: str     # target node UUID

    def to_output_dict(self) -> Dict[str, Any]:
        return {
            "from_node": self.from_node_id,
            "to_node":   self.to_node_id,
        }


# Keep WorkflowConnection for internal use (builder/connect_nodes tools use it)
@dataclass
class WorkflowConnection:
    node: str   # target node NAME (internal)
    type: str
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return {"node": self.node, "type": self.type, "index": self.index}


@dataclass
class SimpleWorkflow:
    name: str
    nodes: List[WorkflowNode] = field(default_factory=list)
    # Internal connection store: {source_name: {conn_type: [[WorkflowConnection]]}}
    connections: Dict[str, Dict[str, List[List[WorkflowConnection]]]] = field(default_factory=dict)

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes.append(node)

    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
        return next((n for n in self.nodes if n.name == name), None)

    # ----------------------------------------------------------------
    # Output serialisation
    # ----------------------------------------------------------------

    def to_output_dict(self) -> Dict[str, Any]:
        """
        Produce the final API output:
        {
            "name": "...",
            "nodes": [ { node_key, nodeId, type, value, expressionExecutionName, parameters } ],
            "edges": [ { from_node, to_node } ]
        }
        """
        nodes_out = [node.to_output_dict() for node in self.nodes]
        edges_out = self._build_edges()

        return {
            "name":  self.name,
            "nodes": nodes_out,
            "edges": edges_out,
        }

    def _build_edges(self) -> List[Dict[str, Any]]:
        """
        Convert internal connections (by node NAME) to output edges (by node UUID).
        """
        # Build a name → id lookup
        name_to_id: Dict[str, str] = {n.name: n.id for n in self.nodes}
        edges: List[Dict[str, Any]] = []
        seen = set()

        for source_name, conn_types in self.connections.items():
            source_id = name_to_id.get(source_name)
            if not source_id:
                continue
            for conn_type, conn_arrays in conn_types.items():
                for conn_array in conn_arrays:
                    for conn in conn_array:
                        target_id = name_to_id.get(conn.node)
                        if not target_id:
                            continue
                        key = (source_id, target_id)
                        if key in seen:
                            continue
                        seen.add(key)
                        edges.append(
                            WorkflowEdge(
                                from_node_id=source_id,
                                to_node_id=target_id,
                            ).to_output_dict()
                        )

        return edges

    def to_dict(self) -> Dict[str, Any]:
        """Legacy internal format (still used by some internal tools)."""
        return {
            "name":  self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": {
                node_name: {
                    ct: [[c.to_dict() for c in arr] for arr in arrays]
                    for ct, arrays in conns.items()
                }
                for node_name, conns in self.connections.items()
            },
        }