# """
# workflow_transformer.py

# Backend workflow JSON  →  Frontend display JSON

# Backend format (input):
# {
#   "name": "...",
#   "nodes": [
#     {
#       "node_key": "<uuid>",
#       "nodeId": "<uuid>",
#       "type": "SCHEDULE TRIGGER" | "MAILCHIMP" | ...,
#       "value": "...",
#       "expressionExecutionName": "...",
#       "parameters": { ... }
#     }
#   ],
#   "edges": [
#     { "from_node": "<uuid>", "to_node": "<uuid>" }
#   ]
# }

# Frontend format (output):
# {
#   "id": <int>,
#   "name": "...",
#   "nodes": [ <full frontend node objects> ],
#   "edges": [ <full frontend edge objects> ],
#   "viewport": { "x": 0, "y": 0, "zoom": 1 },
#   "publish": 0
# }
# """

# import json
# import copy
# from typing import Any

# # .
# # Static metadata per node type  (id, icon, description, nodeTypeActions)
# # Extend this dict as you add more node types
# # .
# S3_BASE = "https://s3.ap-south-1.amazonaws.com/y0-dev-assets/y0-uploads/tools"

# NODE_META = {
#     # type_key            : (actionId, icon_filename,          description,                                       nodeTypeActions)
#     "MANUAL"              : ("2",   "manual.svg",              "Add to start the workflow execution starts",       "trigger"),
#     "SCHEDULE TRIGGER"    : ("131", "Clock.svg",               "Run the flow every day, hour or custom interval",  "trigger"),
#     "WEBHOOK"             : ("12",  "webhook.svg",             "Starts the workflow when a webhook is called",     "trigger"),
#     "MAILCHIMP"           : ("1",   "mailchimp.svg",           "Manage audiences, campaigns, and email marketing", "action"),
#     "GMAIL"               : ("3",   "gmail.svg",               "Send, read, and manage emails via Gmail",          "action"),
#     "SLACK"               : ("5",   "slack.svg",               "Send messages and manage Slack channels",          "action"),
#     "TELEGRAM"            : ("6",   "telegram.svg",            "Send and receive Telegram messages",               "action"),
#     "WHATSAPP BUSINESS CLOUD": ("130", "whatsapp_logo.svg",    "Send and receive WhatsApp Business messages programmatically.", "action"),
#     "EDIT FIELDS (SET)"   : ("135", "edit_files_logo.svg",     "Modify, add, or remove item  fields",              "transformation"),
#     "HTTP REQUEST"        : ("14",  "http.svg",                "Make HTTP requests",                               "action"),
#     "NOTION"              : ("9",   "notion.svg",              "Manage Notion pages and databases",                "action"),
#     "GOOGLE SHEETS"       : ("10",  "google_sheets.svg",       "Read and write Google Sheets data",                "action"),
#     "AIRTABLE"            : ("11",  "airtable.svg",            "Manage Airtable records",                          "action"),
#     "HUBSPOT"             : ("13",  "hubspot.svg",             "Manage HubSpot CRM records",                       "action"),
#     "ASANA"               : ("15",  "asana_logo.svg",          "Manage Asana tasks and projects",                  "action"),
#     "TODOIST"             : ("16",  "todoist_logo.svg",        "Manage Todoist tasks",                             "action"),
#     "SHOPIFY"             : ("17",  "shopify_logo.svg",        "Manage Shopify products and orders",               "action"),
#     "ZOHO CRM"            : ("18",  "zoho_logo.svg",           "Manage Zoho CRM records",                          "action"),
#     "IF"                  : ("20",  "if_logo.svg",             "Route items based on a condition",                 "conditional"),
#     "SWITCH"              : ("21",  "switch_logo.svg",         "Route items based on multiple conditions",         "conditional"),
#     "FILTER"              : ("22",  "filter_logo.svg",         "Filter items based on conditions",                 "conditional"),
#     "LIMIT"               : ("138", "limit_logo.svg",          "Restrict the number of items",                     "transformation"),
#     "MICROSOFT ONEDRIVE"  : ("126", "onedrive_logo.svg",       "Manage files and folders",                         "action"),
# }

# # Folder name per actionId (used in S3 icon URL)
# # We derive this from NODE_META automatically:
# ACTION_ID_TO_FOLDER = {v[0]: v[0] for v in NODE_META.values()}

# # .
# # Helpers
# # .

# def _icon_url(action_id: str, icon_filename: str) -> str:
#     """Build full S3 URL for node icon."""
#     return f"{S3_BASE}/{action_id}/{icon_filename}"


# def _get_meta(node_type: str) -> dict:
#     """Return metadata dict for a node type, with safe fallbacks."""
#     key = node_type.strip().upper()
#     if key in NODE_META:
#         action_id, icon_file, description, node_type_actions = NODE_META[key]
#     else:
#         # Unknown node — use safe defaults
#         action_id  = "0"
#         icon_file  = "default.svg"
#         description = f"{node_type} node"
#         node_type_actions = "action"
#     return {
#         "actionId": action_id,
#         "icon": _icon_url(action_id, icon_file),
#         "description": description,
#         "nodeTypeActions": node_type_actions,
#     }


# def _infer_operation_and_resource(parameters: dict) -> tuple[str | None, str | None]:
#     """Extract operation / resourceName from node parameters if present."""
#     operation    = parameters.get("operation") or None
#     resource_name = parameters.get("resource") or None
#     return operation, resource_name


# def _build_label(node_type: str, parameters: dict) -> str:
#     """Build human-readable label like 'Mailchimp - Send a campaign'."""
#     base = node_type.title()
#     op   = parameters.get("operation")
#     res  = parameters.get("resource")
#     if op and res:
#         return f"{base} - {op.capitalize()} a {res}"
#     elif op:
#         return f"{base} - {op.capitalize()}"
#     return base


# def _build_handle_bounds(node_id: str, node_type_actions: str) -> dict:
#     """
#     Build handleBounds.
#     - Triggers only have a source handle (no input).
#     - Actions / transformations / conditionals have both source and target.
#     """
#     source_handle = {
#         "id": "out",
#         "type": "source",
#         "nodeId": node_id,
#         "position": "right",
#         "x": 316.20001220703125,
#         "y": 30.050018310546875,
#         "width": 6,
#         "height": 6,
#     }
#     target_handle = {
#         "id": "in",
#         "type": "target",
#         "nodeId": node_id,
#         "position": "left",
#         "x": -2.199981689453125,
#         "y": 30.050018310546875,
#         "width": 6,
#         "height": 6,
#     }

#     if node_type_actions == "trigger":
#         return {"source": [source_handle], "target": None}
#     else:
#         return {"source": [source_handle], "target": [target_handle]}


# def _compute_positions(index: int, x_start: int = 368, y_start: int = 240, y_step: int = 96) -> dict:
#     """
#     Auto-layout: stack nodes vertically.
#     First node starts at (x_start, y_start), each subsequent node is y_step lower.
#     """
#     x = x_start
#     y = y_start + index * y_step
#     return {
#         "position": {"x": x, "y": y},
#         "computedPosition": {"x": x, "y": y, "z": 0},
#     }


# # .
# # Core transformer
# # .

# def transform_workflow(backend_json: dict, workflow_id: int = 0) -> dict:
#     """
#     Convert backend workflow JSON → frontend display JSON.

#     Args:
#         backend_json : dict  – Your internal workflow format
#         workflow_id  : int   – Optional numeric ID to embed (default 0)

#     Returns:
#         dict – Frontend-ready JSON
#     """
#     name  = backend_json.get("name", "New Workflow")
#     b_nodes = backend_json.get("nodes", [])
#     b_edges = backend_json.get("edges", [])

#     frontend_nodes = []
#     for idx, b_node in enumerate(b_nodes):
#         node_id    = b_node.get("nodeId") or b_node.get("node_key", f"node-{idx}")
#         node_type  = (b_node.get("value") or b_node.get("type") or "").strip().upper()
#         parameters = b_node.get("parameters") or {}

#         meta               = _get_meta(node_type)
#         action_id          = meta["actionId"]
#         icon               = meta["icon"]
#         description        = meta["description"]
#         node_type_actions  = meta["nodeTypeActions"]

#         operation, resource_name = _infer_operation_and_resource(parameters)
#         label                    = _build_label(node_type, parameters)
#         positions                = _compute_positions(idx)
#         handle_bounds            = _build_handle_bounds(node_id, node_type_actions)

#         frontend_node = {
#             "id": node_id,
#             "type": node_type,
#             "dimensions": {"width": 320, "height": 66},
#             "computedPosition": positions["computedPosition"],
#             "handleBounds": handle_bounds,
#             "selectable": False,
#             "selected": False,
#             "dragging": False,
#             "resizing": False,
#             "initialized": False,
#             "isParent": False,
#             "position": positions["position"],
#             "data": {
#                 "icon": icon,
#                 "color": "#E6E7EC",
#                 "label": label,
#                 "value": copy.deepcopy(parameters),   # node's current param values
#                 "actionId": action_id,
#                 "operation": operation,
#                 "description": description,
#                 "resourceName": resource_name,
#             },
#             "events": {},
#             "parameters": copy.deepcopy(parameters),
#             "nodeTypeActions": node_type_actions,
#         }

#         frontend_nodes.append(frontend_node)

#     # ── Edges .....──
#     frontend_edges = []
#     for b_edge in b_edges:
#         src = b_edge.get("from_node") or b_edge.get("source", "")
#         tgt = b_edge.get("to_node")   or b_edge.get("target", "")
#         edge_id = f"e-{src}-{tgt}"
#         frontend_edges.append({
#             "id": edge_id,
#             "type": "action",
#             "source": src,
#             "target": tgt,
#             "sourceHandle": "out",
#             "targetHandle": "in",
#         })

#     return {
#         "id": workflow_id,
#         "name": name,
#         "nodes": frontend_nodes,
#         "edges": frontend_edges,
#         "viewport": {"x": 0, "y": 0, "zoom": 1},
#         "publish": 0,
#     }


# # .
# # Quick test
# # .

# if __name__ == "__main__":
#     backend_input = {
#         "name": "New Workflow",
#         "nodes": [
#             {
#                 "node_key": "891b5ec1-164b-4149-bd70-704709ddd8c4",
#                 "nodeId": "891b5ec1-164b-4149-bd70-704709ddd8c4",
#                 "type": "trigger",
#                 "value": "SCHEDULE TRIGGER",
#                 "expressionExecutionName": "SCHEDULE TRIGGER",
#                 "parameters": {
#                     "schedule": "0 8 * * *",
#                     "operation": "1"
#                 }
#             },
#             {
#                 "node_key": "0218c1cd-7648-4589-ba5f-26b2a818a012",
#                 "nodeId": "0218c1cd-7648-4589-ba5f-26b2a818a012",
#                 "type": "action",
#                 "value": "TELEGRAM",
#                 "expressionExecutionName": "TELEGRAM",
#                 "parameters": {
#                     "resource": "chat",
#                     "operation": "getall",
#                     "returnAll": False,
#                     "chatId": "your_telegram_chat_id"
#                 }
#             }
#         ],
#         "edges": [
#             {
#                 "from_node": "891b5ec1-164b-4149-bd70-704709ddd8c4",
#                 "to_node": "0218c1cd-7648-4589-ba5f-26b2a818a012"
#             }
#         ]
#     }

#     result = transform_workflow(backend_input, workflow_id=1170)
#     print(json.dumps(result, indent=2, ensure_ascii=False))