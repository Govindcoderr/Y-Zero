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

# types/workflow.py
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────────────────────
# NODE_TYPE_MAP
# Maps node "name" (which IS the value) to its output-format "type" field
# name == value == expressionExecutionName  (all the same string)
# ─────────────────────────────────────────────────────────────────────────────
NODE_TYPE_MAP: Dict[str, str] = {
    # triggers
    "MANUAL":         "trigger",
    "SCHEDULE":       "trigger",
    "WEBHOOK":        "trigger",
    # conditionals
    "IF":             "conditional",
    "SWITCH":         "conditional",
    "FILTER":         "conditional",
}
# Everything not listed above defaults to "action"
_DEFAULT_TYPE = "action"


def _output_type(node_name: str) -> str:
    return NODE_TYPE_MAP.get(node_name, _DEFAULT_TYPE)


# Default operation values per type
_OPERATION_MAP: Dict[str, str] = {
    "trigger":     "1",
    "action":      "3",
    "conditional": "3",
}
# Manual trigger is special — operation "2"
_OPERATION_OVERRIDE: Dict[str, str] = {
    "MANUAL": "2",
}


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowNode
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class WorkflowNode:
    id: str
    name: str       # descriptive label e.g. "Fetch Weather API"
    type: str       # node "value" e.g. "HTTP REQUEST"
    type_version: int
    position: Tuple[int, int]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Internal format."""
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
        Final API output format:
        {
            "node_key": "<uuid>",
            "nodeId":   "<uuid>",
            "type":     "trigger" | "action" | "conditional",
            "value":    "HTTP REQUEST",
            "expressionExecutionName": "HTTP REQUEST",
            "parameters": { "operation": "3", ... }
        }
        """
        out_type  = _output_type(self.type)
        operation = _OPERATION_OVERRIDE.get(self.type, _OPERATION_MAP.get(out_type, "3"))
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
        Merge user-supplied parameters with defaults.
        Parameters come from node_types.json 'parameters' field;
        the LLM fills in the real values.
        """
        base = dict(self.parameters)
        base.setdefault("operation", operation)

        # HTTP REQUEST gets the full scaffold
        if self.type == "HTTP REQUEST":
            base.setdefault("method",           "GET")
            base.setdefault("url",              "")
            base.setdefault("sendBody",         False)
            base.setdefault("sendQuery",        False)
            base.setdefault("sendHeaders",      False)
            base.setdefault("contentType",      "json")
            base.setdefault("specifyBody",      "json")
            base.setdefault("specifyQuery",     "keypair")
            base.setdefault("specifyHeaders",   "keypair")
            base.setdefault("authentication",   "none")
            base.setdefault("bodyParameters",   {"parameters": [{}]})
            base.setdefault("queryParameters",  {"parameters": [{}]})
            base.setdefault("headerParameters", {"parameters": [{}]})

        return base


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowEdge
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class WorkflowEdge:
    from_node_id: str
    to_node_id:   str

    def to_output_dict(self) -> Dict[str, Any]:
        return {"from_node": self.from_node_id, "to_node": self.to_node_id}


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowConnection  (internal — builder uses node names, not UUIDs)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class WorkflowConnection:
    node:  str    # target node NAME
    type:  str
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return {"node": self.node, "type": self.type, "index": self.index}


# ─────────────────────────────────────────────────────────────────────────────
# SimpleWorkflow
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SimpleWorkflow:
    name:        str
    nodes:       List[WorkflowNode] = field(default_factory=list)
    connections: Dict[str, Dict[str, List[List[WorkflowConnection]]]] = field(default_factory=dict)

    # ── public API ────────────────────────────────────────────────

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes.append(node)

    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
        return next((n for n in self.nodes if n.name == name), None)

    # ── output serialisation ──────────────────────────────────────

    def to_output_dict(self) -> Dict[str, Any]:
        """
        Final API response:
        {
            "name":  "...",
            "nodes": [ { node_key, nodeId, type, value, expressionExecutionName, parameters } ],
            "edges": [ { from_node, to_node } ]
        }
        """
        return {
            "name":  self.name,
            "nodes": [n.to_output_dict() for n in self.nodes],
            "edges": self._build_edges(),
        }

    def _build_edges(self) -> List[Dict[str, Any]]:
        """Convert internal name-based connections → UUID-based edges."""
        name_to_id: Dict[str, str] = {n.name: n.id for n in self.nodes}
        edges: List[Dict[str, Any]] = []
        seen = set()

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
                        edges.append(
                            WorkflowEdge(src_id, tgt_id).to_output_dict()
                        )
        return edges

    def to_dict(self) -> Dict[str, Any]:
        """Legacy internal format."""
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