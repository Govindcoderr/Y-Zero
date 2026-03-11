# # backend/types/workflow.py
# from typing import List, Dict, Any, Optional, Tuple
# from dataclasses import dataclass, field

# # ── Global node registry .....──────
# _NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}


# def register_node_types(node_types: List[Dict[str, Any]]) -> None:
#     """NodeSearchEngine init pe call hota hai — ek baar registry populate karo."""
#     global _NODE_REGISTRY
#     _NODE_REGISTRY = {n.get("name", ""): n for n in node_types if n.get("name")}
#     print(f"📋 Node registry: {len(_NODE_REGISTRY)} nodes registered")


# # ── Dynamic nodeType inference .....

# def _infer_output_type(node_type: str) -> str:
#     """
#     100% dynamic — registry se nodeType lo, koi hardcoding nahi.
#     Priority:
#       1. Registry mein nodeType field → use karo directly
#       2. JSONL format: triggers array non-empty → trigger
#       3. Fallback → action
#     """
#     node_data = _NODE_REGISTRY.get(node_type)
#     if node_data:
#         nt = node_data.get("nodeType", "").lower()
#         if nt in ("trigger", "action", "conditional"):
#             return nt
#         # JSONL format — triggers array present aur non-empty
#         if node_data.get("triggers"):
#             return "trigger"
#         # conditional field non-empty
#         if node_data.get("conditional"):
#             return "conditional"
#     return "action"


# def _infer_operation(node_type: str, out_type: str) -> str:
#     """
#     Dynamic operation value — node ki actual actions/triggers array se lo.
#     Fallback: trigger=1, action/conditional=3
#     """
#     node_data = _NODE_REGISTRY.get(node_type)
#     if node_data:
#         all_fields = (
#             node_data.get("actions", []) +
#             node_data.get("triggers", []) +
#             node_data.get("conditional", []) +   # ← conditional field bhi check karo
#             node_data.get("properties", [])
#         )
#         for f in all_fields:
#             if isinstance(f, dict) and f.get("name") == "operation":
#                 default_val = f.get("default", "")
#                 if default_val:
#                     return str(default_val)

#     return "1" if out_type == "trigger" else "3"


# def _extract_defaults(node_type: str) -> Dict[str, Any]:
#     """
#     Node ki actual data se saare default values extract karo.
#     actions + triggers + properties — teeno scan karo.
#     Koi bhi field skip nahi hoga (sirf 'authentication' type skip).
#     """
#     node_data = _NODE_REGISTRY.get(node_type)
#     if not node_data:
#         return {}

#     all_fields = (
#         node_data.get("actions", []) +
#         node_data.get("triggers", []) +
#         node_data.get("conditional", []) +   
#         node_data.get("properties", [])
#     )

#     defaults = {}

#     for f in all_fields:
#         if not isinstance(f, dict):
#             continue

#         name = f.get("name", "").strip()
#         if not name:
#             continue

#         # Authentication/credential fields skip karo
#         if f.get("type") in ("authentication", "baseSelector"):
#             continue

#         default_val = f.get("default")
#         if default_val is None:
#             continue

#         # Empty string skip — koi value nahi hai
#         if default_val == "":
#             continue

#         # Boolean strings normalize karo
#         if isinstance(default_val, str):
#             if default_val.lower() == "true":
#                 default_val = True
#             elif default_val.lower() == "false":
#                 default_val = False

#         defaults[name] = default_val

#     return defaults


# # ── WorkflowNode .

# @dataclass
# class WorkflowNode:
#     id:           str
#     name:         str   # label e.g. "Send Welcome Email"
#     type:         str   # node identifier e.g. "GMAIL", "GITHUB", "IF"
#     type_version: int
#     position:     Tuple[int, int]
#     parameters:   Dict[str, Any] = field(default_factory=dict)

#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             "id":          self.id,
#             "name":        self.name,
#             "type":        self.type,
#             "typeVersion": self.type_version,
#             "position":    list(self.position),
#             "parameters":  self.parameters,
#         }



# def to_output_dict(self) -> Dict[str, Any]:
#     """
#     New backend format — matches frontend canvas JSON spec.
#     """
#     out_type  = _infer_output_type(self.type)   # "trigger" | "action" | "conditional"
#     operation = _infer_operation(self.type, out_type)
#     params    = self._build_output_parameters(operation)

#     # Determine nodeTypeActions
#     if out_type == "trigger":
#         node_type_actions = "trigger"
#     elif out_type == "conditional":
#         node_type_actions = "conditional"
#     else:
#         node_type_actions = "action"

#     # Pull icon/description/actionId from node registry if available
#     node_data  = _NODE_REGISTRY.get(self.type, {})
#     icon_url   = node_data.get("icon", "")
#     description = node_data.get("description", self.name)
#     action_id  = str(node_data.get("actionId", "1"))
#     resource   = params.get("resource", None)
#     operation_val = params.get("operation", None)
#     label      = self.name   # human-readable label from builder

#     x, y = self.position

#     return {
#         "id":   self.id,
#         "type": self.type,           # ← e.g. "MAILCHIMP", "MANUAL", "WHATSAPP BUSINESS CLOUD"
#         "dimensions": {
#             "width":  320,
#             "height": 66
#         },
#         "computedPosition": { "x": x, "y": y, "z": 0 },
#         "handleBounds": {
#             "source": [
#                 {
#                     "id": "out",
#                     "type": "source",
#                     "nodeId": self.id,
#                     "position": "right",
#                     "x": 316.2, "y": 30.05,
#                     "width": 6, "height": 6
#                 }
#             ],
#             "target": None if out_type == "trigger" else [
#                 {
#                     "id": "in",
#                     "type": "target",
#                     "nodeId": self.id,
#                     "position": "left",
#                     "x": -2.2, "y": 30.05,
#                     "width": 6, "height": 6
#                 }
#             ]
#         },
#         "selectable": False,
#         "selected":   False,
#         "dragging":   False,
#         "resizing":   False,
#         "initialized": False,
#         "isParent":   False,
#         "position":   { "x": x, "y": y },
#         "data": {
#             "icon":         icon_url,
#             "color":        "#E6E7EC",
#             "label":        label,
#             "value":        params,          # ← full parameter dict goes here
#             "actionId":     action_id,
#             "operation":    operation_val,
#             "description":  description,
#             "resourceName": resource
#         },
#         "events": {},
#         "parameters":      params,           # ← same as data.value
#         "nodeTypeActions": node_type_actions
#     }

#     def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
#         """
#         Parameter build order:
#         1. Node ki actual data se dynamic defaults
#         2. LLM-provided parameters override karo
#         3. operation always set karo
#         """
#         base = _extract_defaults(self.type)   # step 1: dynamic defaults
#         base.update(self.parameters)           # step 2: LLM override
#         base.setdefault("operation", operation) # step 3: operation ensure
#         return base


# # ── WorkflowEdge .

# @dataclass
# class WorkflowEdge:
#     from_node_id: str
#     to_node_id:   str

#     def to_output_dict(self) -> Dict[str, Any]:
#         return {"from_node": self.from_node_id, "to_node": self.to_node_id}


# # ── WorkflowConnection .....───────

# @dataclass
# class WorkflowConnection:
#     node:  str
#     type:  str
#     index: int

#     def to_dict(self) -> Dict[str, Any]:
#         return {"node": self.node, "type": self.type, "index": self.index}


# # ── SimpleWorkflow .....───────────

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
#         name_to_id = {n.name: n.id for n in self.nodes}
#         edges, seen = [], set()

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
from ..utils.config import Config

# ── Global node registry .....
_NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}

_ICON_BASE_URL = Config._ICON_BASE_URL


def register_node_types(node_types: List[Dict[str, Any]]) -> None:
    """NodeSearchEngine init pe call hota hai — ek baar registry populate karo."""
    global _NODE_REGISTRY
    _NODE_REGISTRY = {n.get("name", ""): n for n in node_types if n.get("name")}
    print(f"📋 Node registry: {len(_NODE_REGISTRY)} nodes registered")


# ── Icon URL builder .....

def _build_icon_url(node_data: Dict[str, Any]) -> str:
    """
    Build full S3 icon URL from node data.
    node_data has: 'id' (e.g. 132) and 'icon' (e.g. 'BigCommerce_logo.svg')
    Returns empty string if icon is null or missing.
    """
    node_id   = node_data.get("id", "")
    icon_file = node_data.get("icon") or ""   # handles null safely
    if node_id and icon_file:
        return f"{_ICON_BASE_URL}/{node_id}/{icon_file}"
    return ""


# ── Dynamic nodeType inference .....

def _infer_output_type(node_type: str) -> str:
    """
    100% dynamic — registry se nodeType lo, koi hardcoding nahi.
    Priority:
      1. Registry mein nodeType field → use karo directly
      2. JSONL format: triggers array non-empty → trigger
      3. conditional array non-empty → conditional
      4. Fallback → action
    """
    node_data = _NODE_REGISTRY.get(node_type)
    if node_data:
        nt = node_data.get("nodeType", "").lower()
        if nt in ("trigger", "action", "conditional"):
            return nt
        if node_data.get("triggers"):
            return "trigger"
        if node_data.get("conditional"):
            return "conditional"
    return "action"


def _infer_operation(node_type: str, out_type: str) -> str:
    """
    Dynamic operation value — node ki actual actions/triggers/conditional array se lo.
    Fallback: trigger=1, action/conditional=3
    """
    node_data = _NODE_REGISTRY.get(node_type)
    if node_data:
        all_fields = (
            node_data.get("actions", []) +
            node_data.get("triggers", []) +
            node_data.get("conditional", []) +
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
    actions + triggers + conditional + properties — sab scan karo.
    authentication/baseSelector type fields skip karo.
    """
    node_data = _NODE_REGISTRY.get(node_type)
    if not node_data:
        return {}

    all_fields = (
        node_data.get("actions", []) +
        node_data.get("triggers", []) +
        node_data.get("conditional", []) +
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


# ── WorkflowNode .

@dataclass
class WorkflowNode:
    id:           str
    name:         str   # label e.g. "Send Welcome Email"
    type:         str   # node identifier e.g. "GMAIL", "GITHUB", "IF"
    type_version: int
    position:     Tuple[int, int]
    parameters:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Internal format — used by builder/configurator agents."""
        return {
            "id":          self.id,
            "name":        self.name,
            "type":        self.type,
            "typeVersion": self.type_version,
            "position":    list(self.position),
            "parameters":  self.parameters,
        }

    def to_output_dict(self) -> Dict[str, Any]:
        """
        Final backend format — matches frontend canvas JSON spec.
        Fully dynamic: all values come from _NODE_REGISTRY or LLM parameters.
        """
        out_type = _infer_output_type(self.type)
        params   = self._build_output_parameters(_infer_operation(self.type, out_type))

        node_data     = _NODE_REGISTRY.get(self.type, {})
        icon_url      = _build_icon_url(node_data)
        description   = node_data.get("description", self.name)
        action_id     = str(node_data.get("id", ""))        # ← node's 'id' field e.g. 132
        resource_val  = params.get("resource", None)
        operation_val = params.get("operation", None)
        label         = self.name

        x, y = self.position

        # Triggers have no incoming handle — they start the flow
        is_trigger = (out_type == "trigger")
        handle_bounds = {
            "source": [
                {
                    "id":       "out",
                    "type":     "source",
                    "nodeId":   self.id,
                    "position": "right",
                    "x":        316.20001220703125,
                    "y":        30.050018310546875,
                    "width":    6,
                    "height":   6
                }
            ],
            "target": None if is_trigger else [
                {
                    "id":       "in",
                    "type":     "target",
                    "nodeId":   self.id,
                    "position": "left",
                    "x":        -2.199981689453125,
                    "y":        30.050018310546875,
                    "width":    6,
                    "height":   6
                }
            ]
        }

        if out_type == "trigger":
            node_type_actions = "trigger"
        elif out_type == "conditional":
            node_type_actions = "conditional"
        else:
            node_type_actions = "action"

        return {
            "id":   self.id,
            "type": self.type,
            "dimensions": {
                "width":  320,
                "height": 66
            },
            "computedPosition": {"x": x, "y": y, "z": 0},
            "handleBounds":     handle_bounds,
            "selectable":       False,
            "selected":         False,
            "dragging":         False,
            "resizing":         False,
            "initialized":      False,
            "isParent":         False,
            "position":         {"x": x, "y": y},
            "data": {
                "icon":         icon_url,
                "color":        "#E6E7EC",
                "label":        label,
                "value":        params,         # full parameter dict
                "actionId":     action_id,
                "operation":    operation_val,
                "description":  description,
                "resourceName": resource_val
            },
            "events":          {},
            "parameters":      params,          # same as data.value
            "nodeTypeActions": node_type_actions
        }

    def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
        """
        Parameter build order:
        1. Node ki actual data se dynamic defaults (actions + triggers + conditional)
        2. LLM-provided parameters override karo
        3. operation always set karo
        """
        base = _extract_defaults(self.type)      # step 1: dynamic defaults
        base.update(self.parameters)             # step 2: LLM override
        base.setdefault("operation", operation)  # step 3: operation ensure
        return base


# ── WorkflowEdge .

@dataclass
class WorkflowEdge:
    from_node_id: str
    to_node_id:   str

    def to_output_dict(self) -> Dict[str, Any]:
        """New edge format — matches frontend canvas spec."""
        return {
            "id":           f"e-{self.from_node_id}-{self.to_node_id}",
            "type":         "action",
            "source":       self.from_node_id,
            "target":       self.to_node_id,
            "sourceHandle": "out",
            "targetHandle": "in"
        }


# ── WorkflowConnection .....───────

@dataclass
class WorkflowConnection:
    node:  str
    type:  str
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return {"node": self.node, "type": self.type, "index": self.index}


# ── SimpleWorkflow .....───────────

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
        """Final backend format — includes id, viewport, publish."""
        return {
            "id":       1,
            "name":     self.name,
            "nodes":    [n.to_output_dict() for n in self.nodes],
            "edges":    self._build_edges(),
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "publish":  0
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
        """Internal format — for agents only."""
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