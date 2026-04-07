# backend/utils/node_normalizer.py
"""
Dynamically normalizes ANY node format into NodeSearchEngine-compatible format.

Supports:
  - node_types.json  (old format: has 'displayName', 'nodeType', 'properties', 'codex')
  - JSONL / JSON     (new format: has 'type', 'name', 'actions', 'triggers', 'category_id')
  - Mixed arrays     (both formats together)

Zero hardcoding — all inference is keyword-based and data-driven.
"""

import json
import os
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Keyword sets for dynamic nodeType inference — extend here if needed
# ---------------------------------------------------------------------------
_TRIGGER_TYPE_KEYWORDS = {
    "TRIGGER", "SCHEDULE", "WEBHOOK", "MANUAL", "CRON", "POLL",
    "LISTEN", "WATCH", "SUBSCRIBE", "EVENT", "TIMER"
}

_CONDITIONAL_TYPE_KEYWORDS = {
    "IF", "SWITCH", "FILTER", "CONDITION", "ROUTER", "BRANCH",
    "SPLIT", "MERGE", "GATE", "DECISION"
}

_CONDITIONAL_NAME_SUBSTRINGS = {
    "if", "switch", "filter", "condition", "router", "branch"
}


def _infer_node_type(node: Dict[str, Any]) -> str:
    """
    Dynamically infer: 'trigger' | 'action' | 'conditional'

    Priority order:
    1. Already has 'nodeType' field → use directly
    2. Has non-empty 'triggers' array → trigger
    3. node 'type' string matches trigger keywords → trigger
    4. node 'type' string matches conditional keywords → conditional
    5. node 'name' contains conditional substrings → conditional
    6. Default → action
    """
    # 1. Already normalized
    existing = node.get("nodeType", "").strip().lower()
    if existing in ("trigger", "action", "conditional"):
        return existing

    # 2. Non-empty triggers array
    if node.get("triggers"):
        return "trigger"

    type_upper = node.get("type", "").upper().replace(" ", "_").replace("&", "AND")
    name_lower = node.get("name", "").lower()

    # 3. Trigger keyword in type
    for kw in _TRIGGER_TYPE_KEYWORDS:
        if kw in type_upper:
            return "trigger"

    # 4. Conditional keyword in type
    for kw in _CONDITIONAL_TYPE_KEYWORDS:
        if kw in type_upper:
            return "conditional"

    # 5. Conditional substring in name
    for substr in _CONDITIONAL_NAME_SUBSTRINGS:
        if substr in name_lower:
            return "conditional"

    return "action"


def _extract_properties(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Unified properties list — handles all formats:
    - New format: 'properties' key present → return as-is
    - JSONL format: merge 'actions' + 'triggers' arrays
    """
    if "properties" in node:
        return node["properties"] or []

    props = []
    for field in node.get("actions") or []:
        if isinstance(field, dict):
            props.append(field)
    for field in node.get("triggers") or []:
        if isinstance(field, dict):
            props.append(field)
    return props


def _extract_aliases(node: Dict[str, Any]) -> List[str]:
    """
    Build alias list for sublimeSearch — zero hardcoding.
    Sources: codex.alias (new format) OR auto-derived from name/type (JSONL).
    """
    # New format
    codex_aliases = node.get("codex", {}).get("alias", [])
    if codex_aliases:
        return list(codex_aliases)

    # JSONL: derive aliases from name and type if they differ
    aliases = []
    name = node.get("name", "").strip()
    type_str = node.get("type", "").strip()

    if name and name.lower() != type_str.lower():
        aliases.append(name)

    # Also add space-separated words from type as aliases (e.g. "GOOGLE CALENDAR" → ["Google", "Calendar"])
    if type_str:
        words = [w.capitalize() for w in type_str.split() if len(w) > 2]
        aliases.extend(words)

    return list(dict.fromkeys(aliases))  # dedupe, preserve order


def _detect_format(node: Dict[str, Any]) -> str:
    """Detect which format this node is in."""
    if node.get("_normalized"):
        return "already_normalized"
    if "displayName" in node and "nodeType" in node:
        return "node_types_json"
    if "actions" in node or ("type" in node and "name" in node and "category_id" in node):
        return "jsonl"
    return "unknown"


def normalize_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single node dict into NodeSearchEngine-compatible format.
    Idempotent — safe to call multiple times.
    """
    fmt = _detect_format(node)

    if fmt == "already_normalized":
        return node

    if fmt == "node_types_json":
        # Already correct format — just tag it and return
        node["_normalized"] = True
        node["_source_format"] = "node_types_json"
        return node

    # JSONL or unknown — full normalization
    node_type = _infer_node_type(node)
    properties = _extract_properties(node)
    aliases = _extract_aliases(node)

    # JSONL: 'type' is the canonical identifier (e.g. "GMAIL", "GITHUB")
    # JSONL: 'name' is the human display name (e.g. "Gmail", "GitHub")
    canonical_name = node.get("type", node.get("name", "")).strip()
    display_name = node.get("name", canonical_name).strip()

    normalized = {
        "id":           node.get("id"),
        "name":         canonical_name,       # NodeSearchEngine uses this as key
        "displayName":  display_name,          # shown to LLM in search results
        "description":  node.get("description", ""),
        "nodeType":     node_type,             # "trigger" | "action" | "conditional"
        "version":      node.get("version", 1),
        "icon":         node.get("icon", ""),
        "category_id":  node.get("category_id"),
        "category_name": node.get("category_name", ""),
        "properties":   properties,   # configurator/update_parameters uses this
        # Preserve raw field arrays so workflow.py can read them for SWITCH/IF skeletons and operation inference
        "actions":      node.get("actions") or [],
        "triggers":     node.get("triggers") or [],
        "conditional":  node.get("conditional") or [],

        "codex": {
            "alias": aliases,
        },
        "class_path":   node.get("class_path") or [],
        "class_name":   node.get("class_name") or [],
        "_normalized":  True,
        "_source_format": fmt,
    }

    return normalized


def normalize_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize a list of nodes. Handles mixed formats."""
    return [normalize_node(n) for n in nodes if isinstance(n, dict)]


def load_and_normalize_nodes(
    *,
    jsonl_path: Optional[str] = None,
    json_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Load nodes from file(s) and normalize them.

    Auto-detection priority (if paths not specified):
      1. NODES_JSONL_PATH env var
      2. NODES_JSON_PATH env var
      3. 'nodes.jsonl' in cwd
      4. 'node_types.json' in cwd  (legacy fallback)

    Both files can be loaded together — results are merged.
    """
    all_nodes: List[Dict[str, Any]] = []

    # Resolve paths
    jsonl_file = jsonl_path or os.getenv("NODES_JSONL_PATH")
    json_file = json_path or os.getenv("NODES_JSON_PATH")

    # Auto-detect if nothing specified
    if not jsonl_file and not json_file:
        if os.path.exists("nodes.jsonl"):
            jsonl_file = "nodes.jsonl"
        elif os.path.exists("node_types.json"):
            json_file = "node_types.json"

    # Load JSONL
    if jsonl_file and os.path.exists(jsonl_file):
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        all_nodes.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Skipping invalid JSONL line: {e}")
        print(f"📦 Loaded {len(all_nodes)} nodes from JSONL: {jsonl_file}")

    # Load JSON (array or object)
    if json_file and os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            all_nodes.extend(data)
        elif isinstance(data, dict):
            # Some formats wrap in {"nodes": [...]}
            all_nodes.extend(data.get("nodes", data.get("node_types", [])))
        print(f"📦 Loaded from JSON: {json_file}")

    if not all_nodes:
        print("⚠️  No node files found. Set NODES_JSONL_PATH or NODES_JSON_PATH env var.")

    normalized = normalize_nodes(all_nodes)
    print(f"✅ Normalized {len(normalized)} nodes total")
    return normalized