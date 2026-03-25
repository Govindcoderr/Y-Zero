
# # backend/types/workflow.py
# from typing import List, Dict, Any, Optional, Tuple
# from dataclasses import dataclass, field
# from ..utils.config import Config

# # ── Global node registry .....
# _NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}

# _ICON_BASE_URL = Config._ICON_BASE_URL


# def register_node_types(node_types: List[Dict[str, Any]]) -> None:
#     """NodeSearchEngine init pe call hota hai — ek baar registry populate karo."""
#     global _NODE_REGISTRY
#     _NODE_REGISTRY = {n.get("name", ""): n for n in node_types if n.get("name")}
#     print(f"📋 Node registry: {len(_NODE_REGISTRY)} nodes registered")


# # ── Icon URL builder .....

# def _build_icon_url(node_data: Dict[str, Any]) -> str:
#     """
#     Build full S3 icon URL from node data.
#     node_data has: 'id' (e.g. 132) and 'icon' (e.g. 'BigCommerce_logo.svg')
#     Returns empty string if icon is null or missing.
#     """
#     node_id   = node_data.get("id", "")
#     icon_file = node_data.get("icon") or ""   # handles null safely
#     if node_id and icon_file:
#         return f"{_ICON_BASE_URL}/{node_id}/{icon_file}"
#     return ""


# # ── Dynamic nodeType inference .....

# def _infer_output_type(node_type: str) -> str:
#     """
#     100% dynamic — registry se nodeType lo, koi hardcoding nahi.
#     Priority:
#       1. Registry mein nodeType field → use karo directly
#       2. JSONL format: triggers array non-empty → trigger
#       3. conditional array non-empty → conditional
#       4. Fallback → action
#     """
#     node_data = _NODE_REGISTRY.get(node_type)
#     if node_data:
#         nt = node_data.get("nodeType", "").lower()
#         if nt in ("trigger", "action", "conditional"):
#             return nt
#         if node_data.get("triggers"):
#             return "trigger"
#         if node_data.get("conditional"):
#             return "conditional"
#     return "action"


# def _infer_operation(node_type: str, out_type: str) -> str:
#     """
#     Dynamic operation value — node ki actual actions/triggers/conditional array se lo.
#     Fallback: trigger=1, action/conditional=3
#     """
#     node_data = _NODE_REGISTRY.get(node_type)
#     if node_data:
#         all_fields = (
#             node_data.get("actions", []) +
#             node_data.get("triggers", []) +
#             node_data.get("conditional", []) +
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
#     actions + triggers + conditional + properties — sab scan karo.
#     authentication/baseSelector type fields skip karo.
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


# def _build_node_geometry(
#     node_id: str,
#     node_type: str,
#     out_type: str,
#     source_handles: Optional[List[str]] = None,
# ) -> Tuple[Dict[str, int], Dict[str, Any]]:
#     """
#     Build frontend node dimensions and handle bounds.

#     Action/trigger nodes use the standard single-output geometry.
#     Conditional nodes need branch-specific source handles so edges anchor
#     to the correct visual ports on the canvas.
#     """
#     is_trigger = (out_type == "trigger")
#     normalized_type = (node_type or "").upper()

#     if normalized_type == "IF":
#         dimensions = {"width": 260, "height": 80}
#         handle_bounds = {
#             "source": [
#                 {
#                     "id": "true",
#                     "type": "source",
#                     "nodeId": node_id,
#                     "position": "right",
#                     "x": 256.171875,
#                     "y": 17.513015747070312,
#                     "width": 6,
#                     "height": 6,
#                 },
#                 {
#                     "id": "false",
#                     "type": "source",
#                     "nodeId": node_id,
#                     "position": "right",
#                     "x": 256.1771240234375,
#                     "y": 56.80000305175781,
#                     "width": 6,
#                     "height": 6,
#                 },
#             ],
#             "target": None if is_trigger else [
#                 {
#                     "id": "in",
#                     "type": "target",
#                     "nodeId": node_id,
#                     "position": "left",
#                     "x": -2.1614990234375,
#                     "y": 37.00520324707031,
#                     "width": 6,
#                     "height": 6,
#                 }
#             ],
#         }
#         return dimensions, handle_bounds

#     if normalized_type == "SWITCH":
#         handles = source_handles or ["out"]
#         spacing = 24
#         height = max(80, 32 + (len(handles) * spacing))
#         center_y = max(0, (height / 2) - 3)
#         start_y = max(8, center_y - ((len(handles) - 1) * spacing / 2))

#         handle_bounds = {
#             "source": [
#                 {
#                     "id": handle_id,
#                     "type": "source",
#                     "nodeId": node_id,
#                     "position": "right",
#                     "x": 256.171875,
#                     "y": start_y + (index * spacing),
#                     "width": 6,
#                     "height": 6,
#                 }
#                 for index, handle_id in enumerate(handles)
#             ],
#             "target": None if is_trigger else [
#                 {
#                     "id": "in",
#                     "type": "target",
#                     "nodeId": node_id,
#                     "position": "left",
#                     "x": -2.1614990234375,
#                     "y": center_y,
#                     "width": 6,
#                     "height": 6,
#                 }
#             ],
#         }
#         return {"width": 260, "height": height}, handle_bounds

#     dimensions = {"width": 320, "height": 66}
#     handle_bounds = {
#         "source": [
#             {
#                 "id": "out",
#                 "type": "source",
#                 "nodeId": node_id,
#                 "position": "right",
#                 "x": 316.20001220703125,
#                 "y": 30.050018310546875,
#                 "width": 6,
#                 "height": 6,
#             }
#         ],
#         "target": None if is_trigger else [
#             {
#                 "id": "in",
#                 "type": "target",
#                 "nodeId": node_id,
#                 "position": "left",
#                 "x": -2.199981689453125,
#                 "y": 30.050018310546875,
#                 "width": 6,
#                 "height": 6,
#             }
#         ],
#     }
#     return dimensions, handle_bounds


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
#         """Internal format — used by builder/configurator agents."""
#         return {
#             "id":          self.id,
#             "name":        self.name,
#             "type":        self.type,
#             "typeVersion": self.type_version,
#             "position":    list(self.position),
#             "parameters":  self.parameters,
#         }

#     def to_output_dict(self, source_handles: Optional[List[str]] = None) -> Dict[str, Any]:
#         """
#         Final backend format — matches frontend canvas JSON spec.
#         Fully dynamic: all values come from _NODE_REGISTRY or LLM parameters.
#         """
#         out_type = _infer_output_type(self.type)
#         params   = self._build_output_parameters(_infer_operation(self.type, out_type))

#         node_data     = _NODE_REGISTRY.get(self.type, {})
#         icon_url      = _build_icon_url(node_data)
#         description   = node_data.get("description", self.name)
#         action_id     = str(node_data.get("id", ""))        # ← node's 'id' field e.g. 132
#         resource_val  = params.get("resource", None)
#         operation_val = params.get("operation", None)
#         label         = self.name

#         x, y = self.position

#         dimensions, handle_bounds = _build_node_geometry(
#             node_id=self.id,
#             node_type=self.type,
#             out_type=out_type,
#             source_handles=source_handles,
#         )

#         if out_type == "trigger":
#             node_type_actions = "trigger"
#         elif out_type == "conditional":
#             node_type_actions = "conditional"
#         else:
#             node_type_actions = "action"

#         return {
#             "id":   self.id,
#             "type": self.type,
#             "dimensions": dimensions,
#             "computedPosition": {"x": x, "y": y, "z": 0},
#             "handleBounds":     handle_bounds,
#             "selectable":       False,
#             "selected":         False,
#             "dragging":         False,
#             "resizing":         False,
#             "initialized":      False,
#             "isParent":         False,
#             "position":         {"x": x, "y": y},
#             "data": {
#                 "icon":         icon_url,
#                 "color":        "#E6E7EC",
#                 "label":        label,
#                 "value":        params,         # full parameter dict
#                 "actionId":     action_id,
#                 "operation":    operation_val,
#                 "description":  description,
#                 "resourceName": resource_val
#             },
#             "events":          {},
#             "parameters":      params,          # same as data.value
#             "nodeTypeActions": node_type_actions
#         }

#     def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
#         """
#         Parameter build order:
#         1. Node ki actual data se dynamic defaults (actions + triggers + conditional)
#         2. LLM-provided parameters override karo
#         3. operation always set karo
#         """
#         base = _extract_defaults(self.type)      # step 1: dynamic defaults
#         base.update(self.parameters)             # step 2: LLM override
#         base.setdefault("operation", operation)  # step 3: operation ensure
#         return base


# # ── WorkflowEdge .

# @dataclass
# class WorkflowEdge:
#     from_node_id: str
#     to_node_id:   str
#     source_handle: str = "out" 
#     target_handle: str = "in"
#     source_x: Optional[float] = None
#     source_y: Optional[float] = None
#     target_x: Optional[float] = None
#     target_y: Optional[float] = None

#     def to_output_dict(self) -> Dict[str, Any]:
#         """New edge format — matches frontend canvas spec."""
#         edge = {
#             "id":           f"e-{self.from_node_id}-{self.to_node_id}",
#             "type":         "action",  # hardcoded for now, can be dynamic if needed
#             "source":       self.from_node_id,
#             "target":       self.to_node_id,
#             "sourceHandle": self.source_handle,
#             "targetHandle": self.target_handle
#         }
#         if self.source_x is not None:
#             edge["sourceX"] = self.source_x
#         if self.source_y is not None:
#             edge["sourceY"] = self.source_y
#         if self.target_x is not None:
#             edge["targetX"] = self.target_x
#         if self.target_y is not None:
#             edge["targetY"] = self.target_y
#         return edge


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
#         """Final backend format — includes id, viewport, publish."""
#         node_source_handles = self._collect_source_handles()
#         node_outputs = [
#             n.to_output_dict(source_handles=node_source_handles.get(n.name))
#             for n in self.nodes
#         ]
#         return {
#             "id":       1,
#             "name":     self.name,
#             "nodes":    node_outputs,
#             "edges":    self._build_edges({node["id"]: node for node in node_outputs}),
#             "viewport": {"x": 0, "y": 0, "zoom": 1},
#             "publish":  0
#         }

#     def _collect_source_handles(self) -> Dict[str, List[str]]:
#         handles_by_node: Dict[str, List[str]] = {}

#         for src_name, conn_types in self.connections.items():
#             src_node = self.get_node_by_name(src_name)
#             src_node_type = src_node.type if src_node else ""
#             ordered_handles: List[str] = []
#             for connection_type, conn_arrays in conn_types.items():
#                 for branch_index, _ in enumerate(conn_arrays):
#                     handle_id = self._connection_to_source_handle(
#                         node_type=src_node_type,
#                         connection_type=connection_type,
#                         branch_index=branch_index,
#                     )
#                     if handle_id not in ordered_handles:
#                         ordered_handles.append(handle_id)

#             if ordered_handles:
#                 handles_by_node[src_name] = ordered_handles

#         return handles_by_node

#     @staticmethod
#     def _connection_to_source_handle(
#         node_type: str,
#         connection_type: str,
#         branch_index: int,
#     ) -> str:
#         normalized_type = (node_type or "").strip().upper()
#         normalized = (connection_type or "").strip()

#         if normalized not in ("", "main", "out"):
#             return normalized

#         if normalized_type == "IF":
#             return "true" if branch_index == 0 else "false"

#         if normalized_type == "SWITCH":
#             return f"output-{branch_index}"

#         if normalized in ("", "main", "out"):
#             return "out"

#         return normalized

#     @staticmethod
#     def _resolve_handle_center(
#         node_output: Dict[str, Any],
#         handle_kind: str,
#         handle_id: str,
#     ) -> Tuple[Optional[float], Optional[float]]:
#         handle_bounds = node_output.get("handleBounds", {}) or {}
#         handles = handle_bounds.get(handle_kind) or []
#         handle = next((h for h in handles if h.get("id") == handle_id), None)
#         if not handle:
#             return None, None

#         position = node_output.get("position", {}) or {}
#         x = float(position.get("x", 0)) + float(handle.get("x", 0)) + (float(handle.get("width", 0)) / 2)
#         y = float(position.get("y", 0)) + float(handle.get("y", 0)) + (float(handle.get("height", 0)) / 2)
#         return x, y

#     def _build_edges(self, node_outputs_by_id: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
#         name_to_id = {n.name: n.id for n in self.nodes}
#         edges, seen = [], set()

#         for src_name, conn_types in self.connections.items():
#             src_id = name_to_id.get(src_name)
#             if not src_id:
#                 continue
#             src_node = self.get_node_by_name(src_name)
#             src_node_type = src_node.type if src_node else ""
#             for connection_type, conn_arrays in conn_types.items():
#                 for branch_index, conn_array in enumerate(conn_arrays):
#                     source_handle = self._connection_to_source_handle(
#                         node_type=src_node_type,
#                         connection_type=connection_type,
#                         branch_index=branch_index,
#                     )
#                     for conn in conn_array:
#                         tgt_id = name_to_id.get(conn.node)
#                         if not tgt_id:
#                             continue
#                         key = (src_id, tgt_id, source_handle)
#                         if key in seen:
#                             continue
#                         seen.add(key)
#                         source_x = source_y = target_x = target_y = None
#                         if node_outputs_by_id:
#                             src_node_output = node_outputs_by_id.get(src_id)
#                             tgt_node_output = node_outputs_by_id.get(tgt_id)
#                             if src_node_output:
#                                 source_x, source_y = self._resolve_handle_center(
#                                     src_node_output,
#                                     "source",
#                                     source_handle,
#                                 )
#                             if tgt_node_output:
#                                 target_x, target_y = self._resolve_handle_center(
#                                     tgt_node_output,
#                                     "target",
#                                     "in",
#                                 )
#                         edges.append(
#                             WorkflowEdge(
#                                 src_id,
#                                 tgt_id,
#                                 source_handle=source_handle,
#                                 target_handle="in",
#                                 source_x=source_x,
#                                 source_y=source_y,
#                                 target_x=target_x,
#                                 target_y=target_y,
#                             ).to_output_dict()
#                         )
#         return edges

#     def to_dict(self) -> Dict[str, Any]:
#         """Internal format — for agents only."""
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
# from collections import deque
# from typing import List, Dict, Any, Optional, Tuple
# from dataclasses import dataclass, field
# from ..utils.config import Config

# # ── Global node registry .....
# _NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}

# _ICON_BASE_URL = Config._ICON_BASE_URL


# def register_node_types(node_types: List[Dict[str, Any]]) -> None:
#     """NodeSearchEngine init pe call hota hai — ek baar registry populate karo."""
#     global _NODE_REGISTRY
#     _NODE_REGISTRY = {n.get("name", ""): n for n in node_types if n.get("name")}
#     print(f"📋 Node registry: {len(_NODE_REGISTRY)} nodes registered")
#     print(f"sample node like GMAIL: {_NODE_REGISTRY.get('SWITCH', {})}")


# # ── Icon URL builder .....

# def _build_icon_url(node_data: Dict[str, Any]) -> str:
#     """
#     Build full S3 icon URL from node data.
#     node_data has: 'id' (e.g. 132) and 'icon' (e.g. 'BigCommerce_logo.svg')
#     Returns empty string if icon is null or missing.
#     """
#     node_id   = node_data.get("id", "")
#     icon_file = node_data.get("icon") or ""   # handles null safely
#     if node_id and icon_file:
#         return f"{_ICON_BASE_URL}/{node_id}/{icon_file}"
#     return ""


# # ── Dynamic nodeType inference .....
# def _infer_output_type(node_type: str) -> str:
#     """
#     100% dynamic — registry se nodeType lo, koi hardcoding nahi.
#     Priority:
#       1. Registry mein nodeType field → use karo directly
#       2. JSONL format: triggers array non-empty → trigger
#       3. conditional array non-empty → conditional
#       4. Fallback → action
#     """
#     node_data = _NODE_REGISTRY.get(node_type)
#     if node_data:
#         nt = node_data.get("nodeType", "").lower()
#         if nt in ("trigger", "action", "conditional"):
#             return nt
#         if node_data.get("triggers"):
#             return "trigger"
#         if node_data.get("conditional"):
#             return "conditional"
#     return "action"

# def resolve_node_role(node: "WorkflowNode", is_start_node: bool) -> str:
#     """
#     Priority 1: node.role explicitly set by builder agent
#     Priority 2: Position-aware fallback — beech ka node kabhi trigger nahi
#     """
#     if node.role in ("trigger", "action", "conditional"):
#         return node.role

#     registry_type = _infer_output_type(node.type)

#     if not is_start_node:
#         return "conditional" if registry_type == "conditional" else "action"

#     return registry_type

# def _infer_operation(node_type: str, out_type: str) -> str:
#     """
#     Dynamic operation value — node ki actual actions/triggers/conditional array se lo.
#     Fallback: trigger=1, action/conditional=3
#     """
#     node_data = _NODE_REGISTRY.get(node_type)
#     if node_data:
#         all_fields = (
#             node_data.get("actions", []) +
#             node_data.get("triggers", []) +
#             node_data.get("conditional", []) +
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
#     actions + triggers + conditional + properties — sab scan karo.
#     authentication/baseSelector type fields skip karo.
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


# def _build_node_geometry(
#     node_id: str,
#     node_type: str,
#     out_type: str,
#     source_handles: Optional[List[str]] = None,
# ) -> Tuple[Dict[str, int], Dict[str, Any]]:
#     """
#     Build frontend node dimensions and handle bounds.

#     Action/trigger nodes use the standard single-output geometry.
#     Conditional nodes need branch-specific source handles so edges anchor
#     to the correct visual ports on the canvas.
#     """
#     is_trigger = (out_type == "trigger")
#     normalized_type = (node_type or "").upper()

#     if normalized_type == "IF":
#         dimensions = {"width": 260, "height": 80}
#         handle_bounds = {
#             "source": [
#                 {
#                     "id": "true",
#                     "type": "source",
#                     "nodeId": node_id,
#                     "position": "right",
#                     "x": 256.171875,
#                     "y": 17.513015747070312,
#                     "width": 6,
#                     "height": 6,
#                 },
#                 {
#                     "id": "false",
#                     "type": "source",
#                     "nodeId": node_id,
#                     "position": "right",
#                     "x": 256.1771240234375,
#                     "y": 56.80000305175781,
#                     "width": 6,
#                     "height": 6,
#                 },
#             ],
#             "target": None if is_trigger else [
#                 {
#                     "id": "in",
#                     "type": "target",
#                     "nodeId": node_id,
#                     "position": "left",
#                     "x": -2.1614990234375,
#                     "y": 37.00520324707031,
#                     "width": 6,
#                     "height": 6,
#                 }
#             ],
#         }
#         return dimensions, handle_bounds

#     if normalized_type == "SWITCH":
#         handles = source_handles or ["out"]
#         spacing = 24
#         height = max(80, 32 + (len(handles) * spacing))
#         center_y = max(0, (height / 2) - 3)
#         start_y = max(8, center_y - ((len(handles) - 1) * spacing / 2))

#         handle_bounds = {
#             "source": [
#                 {
#                     "id": handle_id,
#                     "type": "source",
#                     "nodeId": node_id,
#                     "position": "right",
#                     "x": 256.171875,
#                     "y": start_y + (index * spacing),
#                     "width": 6,
#                     "height": 6,
#                 }
#                 for index, handle_id in enumerate(handles)
#             ],
#             "target": None if is_trigger else [
#                 {
#                     "id": "in",
#                     "type": "target",
#                     "nodeId": node_id,
#                     "position": "left",
#                     "x": -2.1614990234375,
#                     "y": center_y,
#                     "width": 6,
#                     "height": 6,
#                 }
#             ],
#         }
#         return {"width": 260, "height": height}, handle_bounds

#     dimensions = {"width": 320, "height": 66}
#     handle_bounds = {
#         "source": [
#             {
#                 "id": "out",
#                 "type": "source",
#                 "nodeId": node_id,
#                 "position": "right",
#                 "x": 316.20001220703125,
#                 "y": 30.050018310546875,
#                 "width": 6,
#                 "height": 6,
#             }
#         ],
#         "target": None if is_trigger else [
#             {
#                 "id": "in",
#                 "type": "target",
#                 "nodeId": node_id,
#                 "position": "left",
#                 "x": -2.199981689453125,
#                 "y": 30.050018310546875,
#                 "width": 6,
#                 "height": 6,
#             }
#         ],
#     }
#     return dimensions, handle_bounds


# # ── WorkflowNode .
# @dataclass
# class WorkflowNode:
#     id:           str
#     name:         str   # label e.g. "Send Welcome Email"
#     type:         str   # node identifier e.g. "GMAIL", "GITHUB", "IF"
#     type_version: int
#     position:     Tuple[int, int]
#     parameters:   Dict[str, Any] = field(default_factory=dict)
#     role:         Optional[str]  = None  # "trigger" | "action" | "conditional" | None  ← ADD THIS

#     def to_dict(self) -> Dict[str, Any]:
#         """Internal format — used by builder/configurator agents."""
#         return {
#             "id":          self.id,
#             "name":        self.name,
#             "type":        self.type,
#             "typeVersion": self.type_version,
#             "position":    list(self.position),
#             "parameters":  self.parameters,
#         }

#     def to_output_dict(
#         self,
#         source_handles: Optional[List[str]] = None,
#         position_override: Optional[Tuple[int, int]] = None,
#         is_start_node:     bool                     = False,  
#     ) -> Dict[str, Any]:
#         """
#         Final backend format — matches frontend canvas JSON spec.
#         Fully dynamic: all values come from _NODE_REGISTRY or LLM parameters.
#         """
#         out_type = resolve_node_role(self, is_start_node)  
#         params   = self._build_output_parameters(_infer_operation(self.type, out_type))

#         node_data     = _NODE_REGISTRY.get(self.type, {})
#         icon_url      = _build_icon_url(node_data)
#         description   = node_data.get("description", self.name)
#         action_id     = str(node_data.get("id", ""))        # ← node's 'id' field e.g. 132
#         resource_val  = params.get("resource", None)
#         operation_val = params.get("operation", None)
#         label         = self.name

#         x, y = position_override or self.position

#         dimensions, handle_bounds = _build_node_geometry(
#             node_id=self.id,
#             node_type=self.type,
#             out_type=out_type,
#             source_handles=source_handles,
#         )

#         if out_type == "trigger":
#             node_type_actions = "trigger"
#         elif out_type == "conditional":
#             node_type_actions = "conditional"
#         else:
#             node_type_actions = "action"

#         return {
#             "id":   self.id,
#             "type": self.type,
#             "dimensions": dimensions,
#             "computedPosition": {"x": x, "y": y, "z": 0},
#             "handleBounds":     handle_bounds,
#             "selectable":       False,
#             "selected":         False,
#             "dragging":         False,
#             "resizing":         False,
#             "initialized":      False,
#             "isParent":         False,
#             "position":         {"x": x, "y": y},
#             "data": {
#                 "icon":         icon_url,
#                 "color":        "#E6E7EC",
#                 "label":        label,
#                 "value":        params,         # full parameter dict
#                 "actionId":     action_id,
#                 "operation":    operation_val,
#                 "description":  description,
#                 "resourceName": resource_val
#             },
#             "events":          {},
#             "parameters":      params,          # same as data.value
#             "nodeTypeActions": node_type_actions
#         }

#     def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
#         """
#         Parameter build order:
#         1. Node ki actual data se dynamic defaults (actions + triggers + conditional)
#         2. LLM-provided parameters override karo
#         3. operation always set karo
#         """
#         base = _extract_defaults(self.type)      # step 1: dynamic defaults
#         base.update(self.parameters)             # step 2: LLM override
#         base.setdefault("operation", operation)  # step 3: operation ensure
#         return base


# # ── WorkflowEdge .

# @dataclass
# class WorkflowEdge:
#     from_node_id: str
#     to_node_id:   str
#     source_handle: str = "out" 
#     target_handle: str = "in"
#     source_x: Optional[float] = None
#     source_y: Optional[float] = None
#     target_x: Optional[float] = None
#     target_y: Optional[float] = None

#     def to_output_dict(self) -> Dict[str, Any]:
#         """New edge format — matches frontend canvas spec."""
#         edge = {
#             "id":           f"e-{self.from_node_id}-{self.to_node_id}",
#             "type":         "action",  # hardcoded for now, can be dynamic if needed
#             "source":       self.from_node_id,
#             "target":       self.to_node_id,
#             "sourceHandle": self.source_handle,
#             "targetHandle": self.target_handle
#         }
#         if self.source_x is not None:
#             edge["sourceX"] = self.source_x
#         if self.source_y is not None:
#             edge["sourceY"] = self.source_y
#         if self.target_x is not None:
#             edge["targetX"] = self.target_x
#         if self.target_y is not None:
#             edge["targetY"] = self.target_y
#         return edge


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

#     def _find_start_node_ids(self) -> set:
#         all_targets = set()
#         for conn_types in self.connections.values():
#             for arrays in conn_types.values():
#                 for arr in arrays:
#                     for conn in arr:
#                         all_targets.add(conn.node)

#         start_ids = {node.id for node in self.nodes if node.name not in all_targets}

#         if not start_ids and self.nodes:
#             start_ids.add(self.nodes[0].id)

#         return start_ids

#     def to_output_dict(self) -> Dict[str, Any]:
#         """Final backend format — includes id, viewport, publish."""
#         start_ids = self._find_start_node_ids() 
#         node_source_handles = self._collect_source_handles()
#         node_positions = self._compute_canvas_positions()
#         node_outputs = [
#             n.to_output_dict(
#                 source_handles=node_source_handles.get(n.name),
#                 position_override=node_positions.get(n.id),
#                 is_start_node=(n.id in start_ids),  
#             )
#             for n in self.nodes
#         ]
#         return {
#             "id":       1,
#             "name":     self.name,
#             "nodes":    node_outputs,
#             "edges":    self._build_edges({node["id"]: node for node in node_outputs}),
#             "viewport": {"x": 0, "y": 0, "zoom": 1},
#             "publish":  0
#         }

#     def _compute_canvas_positions(self) -> Dict[str, Tuple[int, int]]:
#         """
#         Compute stable canvas coordinates from workflow connections.

#         This keeps straight flows on one horizontal lane and spreads branches
#         vertically so the canvas looks closer to a workflow builder layout.
#         """
#         if not self.nodes:
#             return {}

#         start_x = 80
#         start_y = 240
#         horizontal_gap = 430
#         vertical_gap = 170

#         node_by_name = {node.name: node for node in self.nodes}
#         node_order = {node.id: index for index, node in enumerate(self.nodes)}
#         children_by_id: Dict[str, List[Tuple[int, str]]] = {node.id: [] for node in self.nodes}
#         indegree: Dict[str, int] = {node.id: 0 for node in self.nodes}

#         for src_name, conn_types in self.connections.items():
#             src_node = node_by_name.get(src_name)
#             if not src_node:
#                 continue

#             for _, conn_arrays in conn_types.items():
#                 for branch_index, conn_array in enumerate(conn_arrays):
#                     for conn_index, conn in enumerate(conn_array):
#                         target_node = node_by_name.get(conn.node)
#                         if not target_node:
#                             continue

#                         effective_branch = conn_index if len(conn_arrays) == 1 else branch_index
#                         children_by_id[src_node.id].append((effective_branch, target_node.id))
#                         indegree[target_node.id] += 1

#         root_ids = [node.id for node in self.nodes if indegree[node.id] == 0]
#         if not root_ids:
#             root_ids = [self.nodes[0].id]

#         roots_sorted = sorted(root_ids, key=lambda node_id: node_order[node_id])

#         depth_by_id: Dict[str, int] = {}
#         depth_queue = deque((root_id, 0) for root_id in roots_sorted)
#         while depth_queue:
#             node_id, depth = depth_queue.popleft()
#             if depth <= depth_by_id.get(node_id, -1):
#                 continue

#             depth_by_id[node_id] = depth
#             for _, child_id in children_by_id.get(node_id, []):
#                 depth_queue.append((child_id, depth + 1))

#         lane_by_id: Dict[str, float] = {}
#         for root_index, root_id in enumerate(roots_sorted):
#             lane_by_id[root_id] = float(root_index * 2)

#         lane_queue = deque(roots_sorted)
#         visited: set[str] = set()
#         while lane_queue:
#             node_id = lane_queue.popleft()
#             if node_id in visited:
#                 continue
#             visited.add(node_id)

#             base_lane = lane_by_id.get(node_id, 0.0)
#             outgoing = children_by_id.get(node_id, [])
#             if not outgoing:
#                 continue

#             outgoing_sorted = sorted(
#                 outgoing,
#                 key=lambda item: (item[0], node_order.get(item[1], 10**9)),
#             )
#             center = (len(outgoing_sorted) - 1) / 2

#             for child_index, (_, child_id) in enumerate(outgoing_sorted):
#                 proposed_lane = base_lane + ((child_index - center) * 1.5)
#                 current_lane = lane_by_id.get(child_id)

#                 if current_lane is None:
#                     lane_by_id[child_id] = proposed_lane
#                 else:
#                     lane_by_id[child_id] = (current_lane + proposed_lane) / 2

#                 lane_queue.append(child_id)

#         positions: Dict[str, Tuple[int, int]] = {}
#         fallback_depth = max(depth_by_id.values(), default=0) + 1

#         for fallback_index, node in enumerate(self.nodes):
#             depth = depth_by_id.get(node.id, fallback_depth + fallback_index)
#             lane = lane_by_id.get(node.id, float(fallback_index))
#             positions[node.id] = (
#                 int(start_x + (depth * horizontal_gap)),
#                 int(start_y + (lane * vertical_gap)),
#             )

#         return positions

#     def _collect_source_handles(self) -> Dict[str, List[str]]:
#         handles_by_node: Dict[str, List[str]] = {}

#         for src_name, conn_types in self.connections.items():
#             src_node = self.get_node_by_name(src_name)
#             src_node_type = src_node.type if src_node else ""
#             ordered_handles: List[str] = []
#             for connection_type, conn_arrays in conn_types.items():
#                 for branch_index, _ in enumerate(conn_arrays):
#                     handle_id = self._connection_to_source_handle(
#                         node_type=src_node_type,
#                         connection_type=connection_type,
#                         branch_index=branch_index,
#                     )
#                     if handle_id not in ordered_handles:
#                         ordered_handles.append(handle_id)

#             if ordered_handles:
#                 handles_by_node[src_name] = ordered_handles

#         return handles_by_node

#     @staticmethod
#     def _connection_to_source_handle(
#         node_type: str,
#         connection_type: str,
#         branch_index: int,
#     ) -> str:
#         normalized_type = (node_type or "").strip().upper()
#         normalized = (connection_type or "").strip()

#         if normalized not in ("", "main", "out"):
#             return normalized

#         if normalized_type == "IF":
#             return "true" if branch_index == 0 else "false"

#         if normalized_type == "SWITCH":
#             return f"output-{branch_index}"

#         if normalized in ("", "main", "out"):
#             return "out"

#         return normalized

#     @staticmethod
#     def _resolve_handle_center(
#         node_output: Dict[str, Any],
#         handle_kind: str,
#         handle_id: str,
#     ) -> Tuple[Optional[float], Optional[float]]:
#         handle_bounds = node_output.get("handleBounds", {}) or {}
#         handles = handle_bounds.get(handle_kind) or []
#         handle = next((h for h in handles if h.get("id") == handle_id), None)
#         if not handle:
#             return None, None

#         position = node_output.get("position", {}) or {}
#         x = float(position.get("x", 0)) + float(handle.get("x", 0)) + (float(handle.get("width", 0)) / 2)
#         y = float(position.get("y", 0)) + float(handle.get("y", 0)) + (float(handle.get("height", 0)) / 2)
#         return x, y

#     def _build_edges(self, node_outputs_by_id: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
#         name_to_id = {n.name: n.id for n in self.nodes}
#         edges, seen = [], set()

#         for src_name, conn_types in self.connections.items():
#             src_id = name_to_id.get(src_name)
#             if not src_id:
#                 continue
#             src_node = self.get_node_by_name(src_name)
#             src_node_type = src_node.type if src_node else ""
#             for connection_type, conn_arrays in conn_types.items():
#                 for branch_index, conn_array in enumerate(conn_arrays):
#                     # ── FIX START (added conn_index loop) ──────────────────────────────
#                     # OLD CODE (2 lines):
#                     #   source_handle = self._connection_to_source_handle(
#                     #       node_type=src_node_type,
#                     #       connection_type=connection_type,
#                     #       branch_index=branch_index,
#                     #   )
#                     #   for conn in conn_array:
#                     #
#                     # WHY BROKEN: When LLM puts both Notion and Slack inside the same
#                     # branch array (branch_index=0 for both), _connection_to_source_handle
#                     # returns "true" for every connection — so the false branch never fires.
#                     #
#                     # FIX: Enumerate conn_array too. If all targets are packed into one
#                     # array (len(conn_arrays)==1), use conn_index as the branch index so
#                     # first target → "true", second target → "false", etc.
#                     # If the LLM already spreads targets across separate arrays
#                     # (len(conn_arrays)>1), keep using branch_index as before — no change.
#                     for conn_index, conn in enumerate(conn_array):
#                         effective_branch = (
#                             conn_index if len(conn_arrays) == 1 else branch_index
#                         )
#                         source_handle = self._connection_to_source_handle(
#                             node_type=src_node_type,
#                             connection_type=connection_type,
#                             branch_index=effective_branch,
#                         )
#                     # ── FIX END ────────────────────────────────────────────────────────
#                         tgt_id = name_to_id.get(conn.node)
#                         if not tgt_id:
#                             continue
#                         key = (src_id, tgt_id, source_handle)
#                         if key in seen:
#                             continue
#                         seen.add(key)
#                         source_x = source_y = target_x = target_y = None
#                         if node_outputs_by_id:
#                             src_node_output = node_outputs_by_id.get(src_id)
#                             tgt_node_output = node_outputs_by_id.get(tgt_id)
#                             if src_node_output:
#                                 source_x, source_y = self._resolve_handle_center(
#                                     src_node_output,
#                                     "source",
#                                     source_handle,
#                                 )
#                             if tgt_node_output:
#                                 target_x, target_y = self._resolve_handle_center(
#                                     tgt_node_output,
#                                     "target",
#                                     "in",
#                                 )
#                         edges.append(
#                             WorkflowEdge(
#                                 src_id,
#                                 tgt_id,
#                                 source_handle=source_handle,
#                                 target_handle="in",
#                                 source_x=source_x,
#                                 source_y=source_y,
#                                 target_x=target_x,
#                                 target_y=target_y,
#                             ).to_output_dict()
#                         )
#         return edges

#     def to_dict(self) -> Dict[str, Any]:
#         """Internal format — for agents only."""
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
from collections import deque
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from ..utils.config import Config

# ── Global node registry
_NODE_REGISTRY: Dict[str, Dict[str, Any]] = {}
_ICON_BASE_URL = Config._ICON_BASE_URL


def register_node_types(node_types: List[Dict[str, Any]]) -> None:
    global _NODE_REGISTRY
    _NODE_REGISTRY = {n.get("name", ""): n for n in node_types if n.get("name")}
    print(f"--> Node registry: {len(_NODE_REGISTRY)} nodes registered")


def _build_icon_url(node_data: Dict[str, Any]) -> str:
    node_id   = node_data.get("id", "")
    icon_file = node_data.get("icon") or ""
    if node_id and icon_file:
        return f"{_ICON_BASE_URL}/{node_id}/{icon_file}"
    return ""


def _infer_output_type(node_type: str) -> str:
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


def resolve_node_role(node: "WorkflowNode", is_start_node: bool) -> str:
    if node.role in ("trigger", "action", "conditional"):
        return node.role
    registry_type = _infer_output_type(node.type)
    if not is_start_node:
        return "conditional" if registry_type == "conditional" else "action"
    return registry_type


def _infer_operation(node_type: str, out_type: str) -> str:
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
    Extract default parameter values from the node definition.

    SWITCH and IF get a proper parameter skeleton so the frontend
    knows the mode/conditions structure even before the LLM fills it in.
    All other nodes use generic field-scanning.
    """
    node_data       = _NODE_REGISTRY.get(node_type)
    normalized_type = (node_type or "").upper()

    # ── SWITCH: return a proper skeleton ─────────────────────────
    if normalized_type == "SWITCH":
        return {
            "mode":           "rules",
            "conditions":     [],      # LLM fills with actual conditions
            "rename_output":  False,
            "convert_types":  False,
        }

    # ── IF: return a proper skeleton ──────────────────────────────
    if normalized_type == "IF":
        return {
            "conditions": {
                "options": {
                    "caseSensitive":  True,
                    "leftValue":      "",
                    "typeValidation": "strict",
                },
                "combinator": "and",
                "conditions": [],      # LLM fills with actual conditions
            },
            "options": {},
        }

    # ── All other nodes: scan fields for defaults ─────────────────
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
        if f.get("type") in ("authentication", "baseSelector"):
            continue
        default_val = f.get("default")
        if default_val is None or default_val == "":
            continue
        if isinstance(default_val, str):
            if default_val.lower() == "true":
                default_val = True
            elif default_val.lower() == "false":
                default_val = False
        defaults[name] = default_val

    return defaults


# ── SWITCH output-count helper ────────────────────────────────────

def _count_switch_outputs(parameters: Dict[str, Any]) -> int:
    """
    Derive the number of output branches from SWITCH parameters.

    Priority:
      1. expression mode → number_of_outputs field
      2. rules mode      → length of conditions array
      3. fallback        → 2
    """
    mode = parameters.get("mode", "rules")

    if mode == "expression":
        return max(2, int(parameters.get("number_of_outputs", 2)))

    conditions = parameters.get("conditions", [])
    if isinstance(conditions, list) and conditions:
        return max(2, len(conditions))

    return 2


def _build_switch_geometry(
    node_id:      str,
    output_count: int,
    is_trigger:   bool,
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    """Build SWITCH node geometry with one source handle per output branch."""
    spacing  = 32
    height   = max(80, 40 + output_count * spacing)
    center_y = height / 2 - 3
    start_y  = center_y - (output_count - 1) * spacing / 2

    source_handles = [
        {
            "id":       f"{i}",
            "type":     "source",
            "nodeId":   node_id,
            "position": "right",
            "x":        256.171875,
            "y":        max(8.0, start_y + i * spacing),
            "width":    6,
            "height":   6,
        }
        for i in range(output_count)
    ]

    target_handles = None if is_trigger else [
        {
            "id":       "in",
            "type":     "target",
            "nodeId":   node_id,
            "position": "left",
            "x":        -2.1614990234375,
            "y":        center_y,
            "width":    6,
            "height":   6,
        }
    ]

    return {"width": 260, "height": height}, {"source": source_handles, "target": target_handles}


# ── Geometry dispatcher ───────────────────────────────────────────

def _build_node_geometry(
    node_id:        str,
    node_type:      str,
    out_type:       str,
    source_handles: Optional[List[str]] = None,
    parameters:     Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    is_trigger      = (out_type == "trigger")
    normalized_type = (node_type or "").upper()

    # ── IF ────────────────────────────────────────────────────────
    if normalized_type == "IF":
        dimensions    = {"width": 260, "height": 80}
        handle_bounds = {
            "source": [
                {
                    "id": "true", "type": "source", "nodeId": node_id,
                    "position": "right", "x": 256.171875, "y": 17.513015747070312,
                    "width": 6, "height": 6,
                },
                {
                    "id": "false", "type": "source", "nodeId": node_id,
                    "position": "right", "x": 256.1771240234375, "y": 56.80000305175781,
                    "width": 6, "height": 6,
                },
            ],
            "target": None if is_trigger else [
                {
                    "id": "in", "type": "target", "nodeId": node_id,
                    "position": "left", "x": -2.1614990234375, "y": 37.00520324707031,
                    "width": 6, "height": 6,
                }
            ],
        }
        return dimensions, handle_bounds

    # ── SWITCH ────────────────────────────────────────────────────
    if normalized_type == "SWITCH":
        output_count = _count_switch_outputs(parameters or {})
        # If the caller already knows the handles list, use whichever is bigger
        if source_handles:
            output_count = max(output_count, len(source_handles))
        return _build_switch_geometry(node_id, output_count, is_trigger)

    # ── Standard action / trigger ─────────────────────────────────
    dimensions    = {"width": 320, "height": 66}
    handle_bounds = {
        "source": [
            {
                "id": "out", "type": "source", "nodeId": node_id,
                "position": "right", "x": 316.20001220703125, "y": 30.050018310546875,
                "width": 6, "height": 6,
            }
        ],
        "target": None if is_trigger else [
            {
                "id": "in", "type": "target", "nodeId": node_id,
                "position": "left", "x": -2.199981689453125, "y": 30.050018310546875,
                "width": 6, "height": 6,
            }
        ],
    }
    return dimensions, handle_bounds


# ═══════════════════════════════════════════════════════════════════
# WorkflowNode
# ═══════════════════════════════════════════════════════════════════

@dataclass
class WorkflowNode:
    id:           str
    name:         str
    type:         str
    type_version: int
    position:     Tuple[int, int]
    parameters:   Dict[str, Any] = field(default_factory=dict)
    role:         Optional[str]  = None   # "trigger" | "action" | "conditional" | None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":          self.id,
            "name":        self.name,
            "type":        self.type,
            "typeVersion": self.type_version,
            "position":    list(self.position),
            "parameters":  self.parameters,
        }

    def to_output_dict(
        self,
        source_handles:    Optional[List[str]]       = None,
        position_override: Optional[Tuple[int, int]] = None,
        is_start_node:     bool                      = False,
    ) -> Dict[str, Any]:
        out_type = resolve_node_role(self, is_start_node)
        # Build params first so geometry can read SWITCH condition count
        params   = self._build_output_parameters(_infer_operation(self.type, out_type))

        node_data     = _NODE_REGISTRY.get(self.type, {})
        icon_url      = _build_icon_url(node_data)
        description   = node_data.get("description", self.name)
        action_id     = str(node_data.get("id", ""))
        resource_val  = params.get("resource", None)
        operation_val = params.get("operation", None)
        x, y          = position_override or self.position

        # Pass params so SWITCH geometry uses actual conditions count
        dimensions, handle_bounds = _build_node_geometry(
            node_id=self.id,
            node_type=self.type,
            out_type=out_type,
            source_handles=source_handles,
            parameters=params,
        )

        node_type_actions = (
            "trigger"     if out_type == "trigger"     else
            "conditional" if out_type == "conditional" else
            "action"
        )

        return {
            "id":               self.id,
            "type":             self.type,
            "dimensions":       dimensions,
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
                "label":        self.name,
                "value":        params,
                "actionId":     action_id,
                "operation":    operation_val,
                "description":  description,
                "resourceName": resource_val,
            },
            "events":          {},
            "parameters":      params,
            "nodeTypeActions": node_type_actions,
        }

    def _build_output_parameters(self, operation: str) -> Dict[str, Any]:
        base = _extract_defaults(self.type)   # skeleton (incl. SWITCH mode/conditions)
        base.update(self.parameters)           # LLM values override skeleton
        base.setdefault("operation", operation)
        return base


# ═══════════════════════════════════════════════════════════════════
# WorkflowEdge
# ═══════════════════════════════════════════════════════════════════

@dataclass
class WorkflowEdge:
    from_node_id:  str
    to_node_id:    str
    source_handle: str            = "out"
    target_handle: str            = "in"
    source_x:      Optional[float] = None
    source_y:      Optional[float] = None
    target_x:      Optional[float] = None
    target_y:      Optional[float] = None

    def to_output_dict(self) -> Dict[str, Any]:
        edge = {
            "id":           f"e-{self.from_node_id}-{self.to_node_id}",
            "type":         "action",
            "source":       self.from_node_id,
            "target":       self.to_node_id,
            "sourceHandle": self.source_handle,
            "targetHandle": self.target_handle,
        }
        if self.source_x is not None: edge["sourceX"] = self.source_x
        if self.source_y is not None: edge["sourceY"] = self.source_y
        if self.target_x is not None: edge["targetX"] = self.target_x
        if self.target_y is not None: edge["targetY"] = self.target_y
        return edge


# ═══════════════════════════════════════════════════════════════════
# WorkflowConnection
# ═══════════════════════════════════════════════════════════════════

@dataclass
class WorkflowConnection:
    node:  str
    type:  str
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return {"node": self.node, "type": self.type, "index": self.index}


# ═══════════════════════════════════════════════════════════════════
# SimpleWorkflow
# ═══════════════════════════════════════════════════════════════════

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

    def _find_start_node_ids(self) -> set:
        all_targets = set()
        for conn_types in self.connections.values():
            for arrays in conn_types.values():
                for arr in arrays:
                    for conn in arr:
                        all_targets.add(conn.node)
        start_ids = {node.id for node in self.nodes if node.name not in all_targets}
        if not start_ids and self.nodes:
            start_ids.add(self.nodes[0].id)
        return start_ids

    # ── Public output ─────────────────────────────────────────────

    def to_output_dict(self) -> Dict[str, Any]:
        start_ids           = self._find_start_node_ids()
        node_source_handles = self._collect_source_handles()
        node_positions      = self._compute_canvas_positions()
        node_outputs        = [
            n.to_output_dict(
                source_handles=node_source_handles.get(n.name),
                position_override=node_positions.get(n.id),
                is_start_node=(n.id in start_ids),
            )
            for n in self.nodes
        ]
        return {
            "id":       1,
            "name":     self.name,
            "nodes":    node_outputs,
            "edges":    self._build_edges({node["id"]: node for node in node_outputs}),
            "viewport": {"x": 0, "y": 0, "zoom": 1},
            "publish":  0,
        }

    # ── Canvas layout ─────────────────────────────────────────────

    def _compute_canvas_positions(self) -> Dict[str, Tuple[int, int]]:
        if not self.nodes:
            return {}

        start_x, start_y   = 80, 240
        horizontal_gap      = 430
        vertical_gap        = 170

        node_by_name = {node.name: node for node in self.nodes}
        node_order   = {node.id: i for i, node in enumerate(self.nodes)}
        children_by_id: Dict[str, List[Tuple[int, str]]] = {n.id: [] for n in self.nodes}
        indegree:        Dict[str, int]                   = {n.id: 0 for n in self.nodes}

        for src_name, conn_types in self.connections.items():
            src_node = node_by_name.get(src_name)
            if not src_node:
                continue
            for _, conn_arrays in conn_types.items():
                for bi, conn_array in enumerate(conn_arrays):
                    for ci, conn in enumerate(conn_array):
                        tgt = node_by_name.get(conn.node)
                        if not tgt:
                            continue
                        eff_branch = ci if len(conn_arrays) == 1 else bi
                        children_by_id[src_node.id].append((eff_branch, tgt.id))
                        indegree[tgt.id] += 1

        root_ids     = [n.id for n in self.nodes if indegree[n.id] == 0] or [self.nodes[0].id]
        roots_sorted = sorted(root_ids, key=lambda nid: node_order[nid])

        depth_by_id: Dict[str, int] = {}
        q = deque((rid, 0) for rid in roots_sorted)
        while q:
            nid, d = q.popleft()
            if d <= depth_by_id.get(nid, -1):
                continue
            depth_by_id[nid] = d
            for _, cid in children_by_id.get(nid, []):
                q.append((cid, d + 1))

        lane_by_id: Dict[str, float] = {rid: float(i * 2) for i, rid in enumerate(roots_sorted)}
        lq = deque(roots_sorted)
        visited: set = set()
        while lq:
            nid = lq.popleft()
            if nid in visited:
                continue
            visited.add(nid)
            base  = lane_by_id.get(nid, 0.0)
            outs  = sorted(children_by_id.get(nid, []), key=lambda x: (x[0], node_order.get(x[1], 10**9)))
            if not outs:
                continue
            center = (len(outs) - 1) / 2
            for ci, (_, cid) in enumerate(outs):
                prop = base + (ci - center) * 1.5
                cur  = lane_by_id.get(cid)
                lane_by_id[cid] = prop if cur is None else (cur + prop) / 2
                lq.append(cid)

        fallback_depth = max(depth_by_id.values(), default=0) + 1
        return {
            n.id: (
                int(start_x + depth_by_id.get(n.id, fallback_depth + i) * horizontal_gap),
                int(start_y + lane_by_id.get(n.id, float(i)) * vertical_gap),
            )
            for i, n in enumerate(self.nodes)
        }

    # ── Handle discovery ──────────────────────────────────────────

    def _collect_source_handles(self) -> Dict[str, List[str]]:
        handles_by_node: Dict[str, List[str]] = {}
        for src_name, conn_types in self.connections.items():
            src_node      = self.get_node_by_name(src_name)
            src_node_type = src_node.type if src_node else ""
            ordered: List[str] = []
            for connection_type, conn_arrays in conn_types.items():
                for branch_index, _ in enumerate(conn_arrays):
                    hid = self._connection_to_source_handle(src_node_type, connection_type, branch_index)
                    if hid not in ordered:
                        ordered.append(hid)
            if ordered:
                handles_by_node[src_name] = ordered
        return handles_by_node

    @staticmethod
    def _connection_to_source_handle(
        node_type:       str,
        connection_type: str,
        branch_index:    int,
    ) -> str:
        normalized_type = (node_type or "").strip().upper()
        normalized      = (connection_type or "").strip()

        # Named handle already provided by LLM (e.g. "true", "false", "output-0")
        if normalized not in ("", "main", "out"):
            return normalized

        if normalized_type == "IF":
            return "true" if branch_index == 0 else "false"

        if normalized_type == "SWITCH":
            return f"{branch_index}"

        return "out"

    # ── Edge building ─────────────────────────────────────────────

    @staticmethod
    def _resolve_handle_center(
        node_output: Dict[str, Any],
        handle_kind: str,
        handle_id:   str,
    ) -> Tuple[Optional[float], Optional[float]]:
        handles = (node_output.get("handleBounds") or {}).get(handle_kind) or []
        handle  = next((h for h in handles if h.get("id") == handle_id), None)
        if not handle:
            return None, None
        pos = node_output.get("position", {}) or {}
        x   = float(pos.get("x", 0)) + float(handle.get("x", 0)) + float(handle.get("width",  0)) / 2
        y   = float(pos.get("y", 0)) + float(handle.get("y", 0)) + float(handle.get("height", 0)) / 2
        return x, y

    def _build_edges(
        self,
        node_outputs_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        name_to_id = {n.name: n.id for n in self.nodes}
        edges, seen = [], set()

        for src_name, conn_types in self.connections.items():
            src_id        = name_to_id.get(src_name)
            if not src_id:
                continue
            src_node      = self.get_node_by_name(src_name)
            src_node_type = src_node.type if src_node else ""

            for connection_type, conn_arrays in conn_types.items():
                for branch_index, conn_array in enumerate(conn_arrays):
                    for conn_index, conn in enumerate(conn_array):
                        # Use conn_index as discriminator when LLM packed all targets
                        # into a single array (common for IF/SWITCH branches)
                        effective_branch = conn_index if len(conn_arrays) == 1 else branch_index
                        source_handle    = self._connection_to_source_handle(
                            src_node_type, connection_type, effective_branch
                        )

                        tgt_id = name_to_id.get(conn.node)
                        if not tgt_id:
                            continue
                        key = (src_id, tgt_id, source_handle)
                        if key in seen:
                            continue
                        seen.add(key)

                        sx = sy = tx = ty = None
                        if node_outputs_by_id:
                            so = node_outputs_by_id.get(src_id)
                            to = node_outputs_by_id.get(tgt_id)
                            if so: sx, sy = self._resolve_handle_center(so, "source", source_handle)
                            if to: tx, ty = self._resolve_handle_center(to, "target", "in")

                        edges.append(
                            WorkflowEdge(
                                src_id, tgt_id,
                                source_handle=source_handle,
                                target_handle="in",
                                source_x=sx, source_y=sy,
                                target_x=tx, target_y=ty,
                            ).to_output_dict()
                        )
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