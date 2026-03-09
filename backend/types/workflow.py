# # types/workflow.py
# from typing import List, Dict, Any, Optional, Tuple
# from dataclasses import dataclass, field
# from enum import Enum

# @dataclass
# class WorkflowNode:
#     id: str
#     name: str
#     type: str
#     type_version: int
#     position: Tuple[int, int]
#     parameters: Dict[str, Any] = field(default_factory=dict)
    
#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             "id": self.id,
#             "name": self.name,
#             "type": self.type,
#             "typeVersion": self.type_version,
#             "position": list(self.position),
#             "parameters": self.parameters
#         }

# @dataclass
# class WorkflowConnection:
#     node: str
#     type: str
#     index: int
    
#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             "node": self.node,
#             "type": self.type,
#             "index": self.index
#         }

# @dataclass
# class SimpleWorkflow:
#     name: str
#     nodes: List[WorkflowNode] = field(default_factory=list)
#     connections: Dict[str, Dict[str, List[List[WorkflowConnection]]]] = field(default_factory=dict)
    
#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             "name": self.name,
#             "nodes": [node.to_dict() for node in self.nodes],
#             "connections": {
#                 node_name: {
#                     conn_type: [[conn.to_dict() for conn in conn_list] for conn_list in conn_array]
#                     for conn_type, conn_array in connections.items()
#                 }
#                 for node_name, connections in self.connections.items()
#             }
#         }
    
#     def add_node(self, node: WorkflowNode) -> None:
#         self.nodes.append(node)
    
#     def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
#         return next((node for node in self.nodes if node.id == node_id), None)
    
#     def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
#         return next((node for node in self.nodes if node.name == name), None)





# # types/workflow.py
# from typing import List, Dict, Any, Optional, Tuple
# from dataclasses import dataclass, field
# #
# # NODE_TYPE_MAP
# # Maps node "name" (which IS the value) to its output-format "type" field
# # name == value == expressionExecutionName  (all the same string)#
# NODE_TYPE_MAP: Dict[str, str] = {
#     # triggers
#     "MANUAL":         "trigger",
#     "SCHEDULE":       "trigger",
#     "WEBHOOK":        "trigger",
#     # conditionals
#     "IF":             "conditional",
#     "SWITCH":         "conditional",
#     "FILTER":         "conditional",
# }
# # Everything not listed above defaults to "action"
# _DEFAULT_TYPE = "action"


# def _output_type(node_name: str) -> str:
#     return NODE_TYPE_MAP.get(node_name, _DEFAULT_TYPE)


# # Default operation values per type
# _OPERATION_MAP: Dict[str, str] = {
#     "trigger":     "1",
#     "action":      "3",
#     "conditional": "3",
# }
# # Manual trigger is special — operation "2"
# _OPERATION_OVERRIDE: Dict[str, str] = {
#     "MANUAL": "2",
# }

# #
# # WorkflowNode#
# @dataclass
# class WorkflowNode:
#     id: str
#     name: str       # descriptive label e.g. "Fetch Weather API"
#     type: str       # node "value" e.g. "HTTP REQUEST"
#     type_version: int
#     position: Tuple[int, int]
#     parameters: Dict[str, Any] = field(default_factory=dict)

#     def to_dict(self) -> Dict[str, Any]:
#         """Internal format."""
#         return {
#             "id":          self.id,
#             "name":        self.name,
#             "type":        self.type,
#             "typeVersion": self.type_version,
#             "position":    list(self.position),
#             "parameters":  self.parameters,
#         }

#     def to_output_dict(self) -> Dict[str, Any]:
#         """
#         Final API output format:
#         {
#             "node_key": "<uuid>",
#             "nodeId":   "<uuid>",
#             "type":     "trigger" | "action" | "conditional",
#             "value":    "HTTP REQUEST",
#             "expressionExecutionName": "HTTP REQUEST",
#             "parameters": { "operation": "3", ... }
#         }
#         """
#         out_type  = _output_type(self.type)
#         operation = _OPERATION_OVERRIDE.get(self.type, _OPERATION_MAP.get(out_type, "3"))
#         params    = self._build_output_parameters(operation)

#         return {
#             "node_key":                self.id,
#             "nodeId":                  self.id,
#             "type":                    out_type,
#             "value":                   self.type,
#             "expressionExecutionName": self.type,
#             "parameters":              params,
#         }

#     def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
#         """
#         Merge user-supplied parameters with defaults.
#         Parameters come from node_types.json 'parameters' field;
#         the LLM fills in the real values.
#         """
#         base = dict(self.parameters)
#         base.setdefault("operation", operation)

#         # HTTP REQUEST gets the full scaffold
#         if self.type == "HTTP REQUEST":
#             base.setdefault("method",           "GET")
#             base.setdefault("url",              "")
#             base.setdefault("sendBody",         False)
#             base.setdefault("sendQuery",        False)
#             base.setdefault("sendHeaders",      False)
#             base.setdefault("contentType",      "json")
#             base.setdefault("specifyBody",      "json")
#             base.setdefault("specifyQuery",     "keypair")
#             base.setdefault("specifyHeaders",   "keypair")
#             base.setdefault("authentication",   "none")
#             base.setdefault("bodyParameters",   {"parameters": [{}]})
#             base.setdefault("queryParameters",  {"parameters": [{}]})
#             base.setdefault("headerParameters", {"parameters": [{}]})

#         return base

# #
# # WorkflowEdge#
# @dataclass
# class WorkflowEdge:
#     from_node_id: str
#     to_node_id:   str

#     def to_output_dict(self) -> Dict[str, Any]:
#         return {"from_node": self.from_node_id, "to_node": self.to_node_id}

# #
# # WorkflowConnection  (internal — builder uses node names, not UUIDs)#
# @dataclass
# class WorkflowConnection:
#     node:  str    # target node NAME
#     type:  str
#     index: int

#     def to_dict(self) -> Dict[str, Any]:
#         return {"node": self.node, "type": self.type, "index": self.index}

# #
# # SimpleWorkflow#
# @dataclass
# class SimpleWorkflow:
#     name:        str
#     nodes:       List[WorkflowNode] = field(default_factory=list)
#     connections: Dict[str, Dict[str, List[List[WorkflowConnection]]]] = field(default_factory=dict)

#     # ── public API ────────────────────────────────────────────────

#     def add_node(self, node: WorkflowNode) -> None:
#         self.nodes.append(node)

#     def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
#         return next((n for n in self.nodes if n.id == node_id), None)

#     def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
#         return next((n for n in self.nodes if n.name == name), None)

#     # ── output serialisation ──────────────────────────────────────

#     def to_output_dict(self) -> Dict[str, Any]:
#         """
#         Final API response:
#         {
#             "name":  "...",
#             "nodes": [ { node_key, nodeId, type, value, expressionExecutionName, parameters } ],
#             "edges": [ { from_node, to_node } ]
#         }
#         """
#         return {
#             "name":  self.name,
#             "nodes": [n.to_output_dict() for n in self.nodes],
#             "edges": self._build_edges(),
#         }

#     def _build_edges(self) -> List[Dict[str, Any]]:
#         """Convert internal name-based connections → UUID-based edges."""
#         name_to_id: Dict[str, str] = {n.name: n.id for n in self.nodes}
#         edges: List[Dict[str, Any]] = []
#         seen = set()

#         for src_name, conn_types in self.connections.items():
#             src_id = name_to_id.get(src_name)
#             if not src_id:
#                 continue
#             for _, conn_arrays in conn_types.items():
#                 for conn_array in conn_arrays:
#                     for conn in conn_array:
#                         tgt_id = name_to_id.get(conn.node)
#                         if not tgt_id:
#                             continue
#                         key = (src_id, tgt_id)
#                         if key in seen:
#                             continue
#                         seen.add(key)
#                         edges.append(
#                             WorkflowEdge(src_id, tgt_id).to_output_dict()
#                         )
#         return edges

#     def to_dict(self) -> Dict[str, Any]:
#         """Legacy internal format."""
#         return {
#             "name":  self.name,
#             "nodes": [n.to_dict() for n in self.nodes],
#             "connections": {
#                 node_name: {
#                     ct: [[c.to_dict() for c in arr] for arr in arrays]
#                     for ct, arrays in conns.items()
#                 }
#                 for node_name, conns in self.connections.items()
#             },
#         }









# # backend/types/workflow.py
# from typing import List, Dict, Any, Optional, Tuple
# from dataclasses import dataclass, field

# # ── Global node registry ──────────────────────────────────────────────────────
# # NodeSearchEngine load hone ke baad yahan inject hota hai
# # WorkflowNode.to_output_dict() isko use karta hai dynamic defaults ke liye
# _NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}


# def register_node_types(node_types: List[Dict[str, Any]]) -> None:
#     """
#     NodeSearchEngine init pe call karo — node type → raw node data mapping banao.
#     Key = node 'name' field (e.g. 'GMAIL', 'GITHUB', 'AIRTABLE')
#     """
#     global _NODE_REGISTRY
#     _NODE_REGISTRY = {n.get("name", ""): n for n in node_types if n.get("name")}
#     print(f"📋 Node registry populated: {len(_NODE_REGISTRY)} nodes")


# def _get_node_data(node_type: str) -> Optional[Dict[str, Any]]:
#     """Registry se node raw data fetch karo."""
#     return _NODE_REGISTRY.get(node_type)


# # ── nodeType inference — fully dynamic ───────────────────────────────────────

# _TRIGGER_KEYWORDS    = {"TRIGGER", "SCHEDULE", "WEBHOOK", "MANUAL", "CRON", "POLL"}
# _CONDITIONAL_KEYWORDS = {"IF", "SWITCH", "FILTER", "CONDITION", "ROUTER", "BRANCH"}


# def _infer_output_type(node_type: str) -> str:
#     """
#     Dynamically infer 'trigger' | 'action' | 'conditional'
#     Priority: registry nodeType field → keyword match → default action
#     """
#     node_data = _get_node_data(node_type)
#     if node_data:
#         nt = node_data.get("nodeType", "").lower()
#         if nt in ("trigger", "action", "conditional"):
#             return nt

#         # JSONL format: triggers array non-empty → trigger
#         if node_data.get("triggers"):
#             return "trigger"

#     # Keyword fallback
#     upper = node_type.upper()
#     for kw in _TRIGGER_KEYWORDS:
#         if kw in upper:
#             return "trigger"
#     for kw in _CONDITIONAL_KEYWORDS:
#         if kw in upper:
#             return "conditional"

#     return "action"


# def _infer_operation(node_type: str, out_type: str) -> str:
#     """
#     Dynamically infer operation value from node data.
#     Falls back to type-based defaults.
#     """
#     node_data = _get_node_data(node_type)
#     if node_data:
#         # actions array mein 'operation' field ka default value dhundo
#         for field_def in node_data.get("actions", []) + node_data.get("triggers", []):
#             if field_def.get("name") == "operation":
#                 default_val = field_def.get("default", "")
#                 if default_val:
#                     return str(default_val)

#     # Type-based fallback
#     defaults = {"trigger": "1", "action": "3", "conditional": "3"}
#     return defaults.get(out_type, "3")


# def _build_defaults_from_node_data(node_type: str) -> Dict[str, Any]:
#     """
#     Node ki actual actions/triggers/properties array se default values extract karo.
#     Yeh DYNAMIC hai — koi hardcoding nahi.
#     """
#     node_data = _get_node_data(node_type)
#     if not node_data:
#         return {}

#     defaults = {}

#     # actions + triggers dono scan karo
#     all_fields = node_data.get("actions", []) + node_data.get("triggers", [])
#     # new format (node_types.json) ke liye
#     all_fields += node_data.get("properties", [])

#     for field_def in all_fields:
#         if not isinstance(field_def, dict):
#             continue

#         field_name = field_def.get("name", "").strip()
#         if not field_name:
#             continue

#         # authentication type fields skip karo (credential_id etc.)
#         if field_def.get("type") == "authentication":
#             continue

#         default_val = field_def.get("default")

#         # Default value present hai toh set karo
#         if default_val is not None and default_val != "":
#             # Boolean strings normalize karo
#             if isinstance(default_val, str):
#                 if default_val.lower() == "true":
#                     default_val = True
#                 elif default_val.lower() == "false":
#                     default_val = False

#             defaults[field_name] = default_val

#     return defaults


# # ── WorkflowNode ─────────────────────────────────────────────────────────────

# @dataclass
# class WorkflowNode:
#     id:           str
#     name:         str    # descriptive label e.g. "Fetch Weather API"
#     type:         str    # node identifier e.g. "GMAIL", "GITHUB"
#     type_version: int
#     position:     Tuple[int, int]
#     parameters:   Dict[str, Any] = field(default_factory=dict)

#     def to_dict(self) -> Dict[str, Any]:
#         """Internal format."""
#         return {
#             "id":          self.id,
#             "name":        self.name,
#             "type":        self.type,
#             "typeVersion": self.type_version,
#             "position":    list(self.position),
#             "parameters":  self.parameters,
#         }

#     def to_output_dict(self) -> Dict[str, Any]:
#         """Final API output format — fully dynamic, zero hardcoding."""
#         out_type  = _infer_output_type(self.type)
#         operation = _infer_operation(self.type, out_type)
#         params    = self._build_output_parameters(operation)

#         return {
#             "node_key":                self.id,
#             "nodeId":                  self.id,
#             "type":                    out_type,
#             "value":                   self.type,
#             "expressionExecutionName": self.type,
#             "parameters":              params,
#         }

#     def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
#         """
#         Dynamic parameter building:
#         1. Node ki actual data se defaults extract karo
#         2. LLM-provided parameters se override karo
#         3. operation field ensure karo
#         """
#         # Step 1: Node data se dynamic defaults
#         base = _build_defaults_from_node_data(self.type)

#         # Step 2: LLM parameters override karo (yeh most specific hain)
#         base.update(self.parameters)

#         # Step 3: operation always present hona chahiye
#         base.setdefault("operation", operation)

#         return base


# # ── WorkflowEdge ─────────────────────────────────────────────────────────────

# @dataclass
# class WorkflowEdge:
#     from_node_id: str
#     to_node_id:   str

#     def to_output_dict(self) -> Dict[str, Any]:
#         return {"from_node": self.from_node_id, "to_node": self.to_node_id}


# # ── WorkflowConnection ───────────────────────────────────────────────────────

# @dataclass
# class WorkflowConnection:
#     node:  str
#     type:  str
#     index: int

#     def to_dict(self) -> Dict[str, Any]:
#         return {"node": self.node, "type": self.type, "index": self.index}


# # ── SimpleWorkflow ───────────────────────────────────────────────────────────

# @dataclass
# class SimpleWorkflow:
#     name:        str
#     nodes:       List[WorkflowNode] = field(default_factory=list)
#     connections: Dict[str, Dict[str, List[List[WorkflowConnection]]]] = field(default_factory=dict)

#     def add_node(self, node: WorkflowNode) -> None:
#         self.nodes.append(node)

#     def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
#         return next((n for n in self.nodes if n.id == node_id), None)

#     def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
#         return next((n for n in self.nodes if n.name == name), None)

#     def to_output_dict(self) -> Dict[str, Any]:
#         return {
#             "name":  self.name,
#             "nodes": [n.to_output_dict() for n in self.nodes],
#             "edges": self._build_edges(),
#         }

#     def _build_edges(self) -> List[Dict[str, Any]]:
#         name_to_id: Dict[str, str] = {n.name: n.id for n in self.nodes}
#         edges: List[Dict[str, Any]] = []
#         seen = set()

#         for src_name, conn_types in self.connections.items():
#             src_id = name_to_id.get(src_name)
#             if not src_id:
#                 continue
#             for _, conn_arrays in conn_types.items():
#                 for conn_array in conn_arrays:
#                     for conn in conn_array:
#                         tgt_id = name_to_id.get(conn.node)
#                         if not tgt_id:
#                             continue
#                         key = (src_id, tgt_id)
#                         if key in seen:
#                             continue
#                         seen.add(key)
#                         edges.append(WorkflowEdge(src_id, tgt_id).to_output_dict())
#         return edges

#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             "name":  self.name,
#             "nodes": [n.to_dict() for n in self.nodes],
#             "connections": {
#                 node_name: {
#                     ct: [[c.to_dict() for c in arr] for arr in arrays]
#                     for ct, arrays in conns.items()
#                 }
#                 for node_name, conns in self.connections.items()
#             },
#         }






# backend/types/workflow.py
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

# ── Global node registry ──────────────────────────────────────────────────────
_NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_node_types(node_types: List[Dict[str, Any]]) -> None:
    """NodeSearchEngine init pe call hota hai — ek baar registry populate karo."""
    global _NODE_REGISTRY
    _NODE_REGISTRY = {n.get("name", ""): n for n in node_types if n.get("name")}
    print(f"📋 Node registry: {len(_NODE_REGISTRY)} nodes registered")


# ── Dynamic nodeType inference ────────────────────────────────────────────────

def _infer_output_type(node_type: str) -> str:
    """
    100% dynamic — registry se nodeType lo, koi hardcoding nahi.
    Priority:
      1. Registry mein nodeType field → use karo directly
      2. JSONL format: triggers array non-empty → trigger
      3. Fallback → action
    """
    node_data = _NODE_REGISTRY.get(node_type)
    if node_data:
        nt = node_data.get("nodeType", "").lower()
        if nt in ("trigger", "action", "conditional"):
            return nt
        # JSONL format — triggers array present aur non-empty
        if node_data.get("triggers"):
            return "trigger"
        # conditional field non-empty
        if node_data.get("conditional"):
            return "conditional"
    return "action"


def _infer_operation(node_type: str, out_type: str) -> str:
    """
    Dynamic operation value — node ki actual actions/triggers array se lo.
    Fallback: trigger=1, action/conditional=3
    """
    node_data = _NODE_REGISTRY.get(node_type)
    if node_data:
        all_fields = (
            node_data.get("actions", []) +
            node_data.get("triggers", []) +
            node_data.get("properties", [])
        )
        for f in all_fields:
            if isinstance(f, dict) and f.get("name") == "operation":
                default_val = f.get("default", "")
                if default_val:
                    return str(default_val)

    return "1" if out_type == "trigger" else "3"


def _extract_defaults(node_type: str) -> Dict[str, Any]:
    """
    Node ki actual data se saare default values extract karo.
    actions + triggers + properties — teeno scan karo.
    Koi bhi field skip nahi hoga (sirf 'authentication' type skip).
    """
    node_data = _NODE_REGISTRY.get(node_type)
    if not node_data:
        return {}

    all_fields = (
        node_data.get("actions", []) +
        node_data.get("triggers", []) +
        node_data.get("properties", [])
    )

    defaults = {}

    for f in all_fields:
        if not isinstance(f, dict):
            continue

        name = f.get("name", "").strip()
        if not name:
            continue

        # Authentication/credential fields skip karo
        if f.get("type") in ("authentication", "baseSelector"):
            continue

        default_val = f.get("default")
        if default_val is None:
            continue

        # Empty string skip — koi value nahi hai
        if default_val == "":
            continue

        # Boolean strings normalize karo
        if isinstance(default_val, str):
            if default_val.lower() == "true":
                default_val = True
            elif default_val.lower() == "false":
                default_val = False

        defaults[name] = default_val

    return defaults


# ── WorkflowNode ─────────────────────────────────────────────────────────────

@dataclass
class WorkflowNode:
    id:           str
    name:         str   # label e.g. "Send Welcome Email"
    type:         str   # node identifier e.g. "GMAIL", "GITHUB", "IF"
    type_version: int
    position:     Tuple[int, int]
    parameters:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":          self.id,
            "name":        self.name,
            "type":        self.type,
            "typeVersion": self.type_version,
            "position":    list(self.position),
            "parameters":  self.parameters,
        }

    def to_output_dict(self) -> Dict[str, Any]:
        """Final API output — fully dynamic, zero hardcoding."""
        out_type  = _infer_output_type(self.type)
        operation = _infer_operation(self.type, out_type)
        params    = self._build_output_parameters(operation)

        return {
            "node_key":                self.id,
            "nodeId":                  self.id,
            "type":                    out_type,
            "value":                   self.type,
            "expressionExecutionName": self.type,
            "parameters":              params,
        }

    def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
        """
        Parameter build order:
        1. Node ki actual data se dynamic defaults
        2. LLM-provided parameters override karo
        3. operation always set karo
        """
        base = _extract_defaults(self.type)   # step 1: dynamic defaults
        base.update(self.parameters)           # step 2: LLM override
        base.setdefault("operation", operation) # step 3: operation ensure
        return base


# ── WorkflowEdge ─────────────────────────────────────────────────────────────

@dataclass
class WorkflowEdge:
    from_node_id: str
    to_node_id:   str

    def to_output_dict(self) -> Dict[str, Any]:
        return {"from_node": self.from_node_id, "to_node": self.to_node_id}


# ── WorkflowConnection ───────────────────────────────────────────────────────

@dataclass
class WorkflowConnection:
    node:  str
    type:  str
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return {"node": self.node, "type": self.type, "index": self.index}


# ── SimpleWorkflow ───────────────────────────────────────────────────────────

@dataclass
class SimpleWorkflow:
    name:        str
    nodes:       List[WorkflowNode] = field(default_factory=list)
    connections: Dict[str, Dict[str, List[List[WorkflowConnection]]]] = field(default_factory=dict)

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes.append(node)

    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
        return next((n for n in self.nodes if n.name == name), None)

    def to_output_dict(self) -> Dict[str, Any]:
        return {
            "name":  self.name,
            "nodes": [n.to_output_dict() for n in self.nodes],
            "edges": self._build_edges(),
        }

    def _build_edges(self) -> List[Dict[str, Any]]:
        name_to_id = {n.name: n.id for n in self.nodes}
        edges, seen = [], set()

        for src_name, conn_types in self.connections.items():
            src_id = name_to_id.get(src_name)
            if not src_id:
                continue
            for _, conn_arrays in conn_types.items():
                for conn_array in conn_arrays:
                    for conn in conn_array:
                        tgt_id = name_to_id.get(conn.node)
                        if not tgt_id:
                            continue
                        key = (src_id, tgt_id)
                        if key in seen:
                            continue
                        seen.add(key)
                        edges.append(WorkflowEdge(src_id, tgt_id).to_output_dict())
        return edges

    def to_dict(self) -> Dict[str, Any]:
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