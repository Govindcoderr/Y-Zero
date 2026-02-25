# # engines/node_search_engine.py
# from typing import List, Optional, Dict, Any
# from ..types.nodes import NodeSearchResult, NodeDetails
# import re

# class NodeSearchEngine:
#     def __init__(self, node_types: List[Dict[str, Any]]):
#         self.node_types = node_types
#         self._build_index()
    
#     def _build_index(self):
#         """Build search index for faster lookups"""
#         self.name_index = {}
#         self.keyword_index = {}
        
#         for node in self.node_types:
#             name = node.get("name", "").lower()
#             display_name = node.get("displayName", "").lower()
#             description = node.get("description", "").lower()
            
#             # Index by name
#             self.name_index[name] = node
            
#             # Index keywords
#             keywords = set(name.split(".") + display_name.split() + description.split())
#             for keyword in keywords:
#                 if len(keyword) > 2:
#                     if keyword not in self.keyword_index:
#                         self.keyword_index[keyword] = []
#                     self.keyword_index[keyword].append(node)
    
#     def search_by_name(self, query: str, limit: int = 10) -> List[NodeSearchResult]:
#         """Search nodes by name or description"""
#         query_lower = query.lower()
#         results = []
        
#         for node_type in self.node_types:
#             score = 0.0
#             name = node_type.get("name", "").lower()
#             display_name = node_type.get("displayName", "").lower()
#             description = node_type.get("description", "").lower()
            
#             # Exact name match
#             if query_lower == name:
#                 score += 100
#             elif query_lower in name:
#                 score += 80
            
#             # Display name match
#             if query_lower == display_name:
#                 score += 90
#             elif query_lower in display_name:
#                 score += 70
            
#             # Description match
#             if query_lower in description:
#                 score += 50
            
#             # Keyword match
#             query_words = query_lower.split()
#             for word in query_words:
#                 if word in name:
#                     score += 20
#                 if word in display_name:
#                     score += 15
#                 if word in description:
#                     score += 10
            
#             if score > 0:
#                 results.append(NodeSearchResult(
#                     name=node_type.get("name", ""),
#                     display_name=node_type.get("displayName", ""),
#                     description=node_type.get("description", "No description"),
#                     version=self._get_latest_version(node_type),
#                     inputs=node_type.get("inputs", []),
#                     outputs=node_type.get("outputs", []),
#                     score=score
#                 ))
        
#         # Sort by score and return top results
#         results.sort(key=lambda x: x.score, reverse=True)
#         return results[:limit]
    
#     def _get_latest_version(self, node_type: Dict[str, Any]) -> int:
#         """Get latest version of a node type"""
#         version = node_type.get("version", 1)
#         if isinstance(version, list):
#             return max(version)
#         return version
    
#     def get_node_details(self, node_name: str, version: int) -> Optional[NodeDetails]:
#         """Get detailed information about a specific node"""
#         node_type = next(
#             (nt for nt in self.node_types 
#              if nt.get("name") == node_name and self._matches_version(nt, version)),
#             None
#         )
        
#         if not node_type:
#             return None
        
#         return NodeDetails(
#             name=node_type.get("name", ""),
#             display_name=node_type.get("displayName", ""),
#             description=node_type.get("description", "No description"),
#             properties=node_type.get("properties", []),
#             inputs=node_type.get("inputs", []),
#             outputs=node_type.get("outputs", []),
#             version=self._get_latest_version(node_type)
#         )
    
#     def _matches_version(self, node_type: Dict[str, Any], version: int) -> bool:
#         """Check if node type matches version"""
#         node_version = node_type.get("version", 1)
#         if isinstance(node_version, list):
#             return version in node_version
#         return node_version == version
    
#     def search_by_category(self, category: str) -> List[NodeSearchResult]:
#         """Search nodes by category or group"""
#         category_lower = category.lower()
#         results = []
        
#         for node_type in self.node_types:
#             groups = node_type.get("group", [])
#             if isinstance(groups, str):
#                 groups = [groups]
            
#             if any(category_lower in g.lower() for g in groups):
#                 results.append(NodeSearchResult(
#                     name=node_type.get("name", ""),
#                     display_name=node_type.get("displayName", ""),
#                     description=node_type.get("description", "No description"),
#                     version=self._get_latest_version(node_type),
#                     inputs=node_type.get("inputs", []),
#                     outputs=node_type.get("outputs", []),
#                     score=100
#                 ))
        
#         return results

# engines/node_search_engine.py

"""
NodeSearchEngine — Python port inspired by n8n's node-search-engine.ts

Node types: trigger | action | conditional  (no inputs/outputs fields)
Node name = the "value" used directly in the output JSON (e.g. "HTTP REQUEST", "TELEGRAM")

Key design:
- sublimeSearch with weighted keys: displayName > name > codex.alias > description
- dedupeNodes — latest version wins
- searchByName(query, limit)
- searchByNodeType(nodeType, limit)
- formatResult(result) — XML string for LLM
- resolve_node_type(requested) — fuzzy → exact node name
"""
from __future__ import annotations
from difflib import SequenceMatcher
from typing import List, Optional, Dict, Any, Tuple
from ..types.nodes import NodeSearchResult, NodeDetails

#
# NODE_SEARCH_KEYS  (mirrors n8n exactly)#
NODE_SEARCH_KEYS = [
    {"key": "displayName", "weight": 1.5},
    {"key": "name",        "weight": 1.3},
    {"key": "codex.alias", "weight": 1.0},
    {"key": "description", "weight": 0.7},
]

#
# sublimeSearch  (Python port of @n8n/utils sublimeSearch)#
def _get_field_value(node: Dict[str, Any], key: str) -> str:
    """Resolve dotted keys like 'codex.alias'. Returns joined string for lists."""
    parts = key.split(".")
    val = node
    for p in parts:
        val = val.get(p, "") if isinstance(val, dict) else ""
    if isinstance(val, list):
        return " ".join(str(v) for v in val)
    return str(val) if val else ""


def _field_score(query: str, text: str, weight: float) -> float:
    """Weighted fuzzy score for one field — mirrors sublimeSearch scoring."""
    if not query or not text:
        return 0.0
    q, t = query.lower(), text.lower()

    if q == t:                  return weight * 1.00
    if t.startswith(q):         return weight * 0.90
    if q in t:                  return weight * 0.80

    words = q.split()
    hits  = sum(1 for w in words if w in t)
    ratio = hits / len(words)
    if ratio == 1.0:            return weight * 0.75
    if ratio > 0.0:             return weight * ratio * 0.70

    fuzzy = SequenceMatcher(None, q, t).ratio()
    if fuzzy > 0.45:            return weight * fuzzy * 0.55

    return 0.0


def sublime_search(
    query: str,
    nodes: List[Dict[str, Any]],
    search_keys: List[Dict[str, Any]],
) -> List[Tuple[float, Dict[str, Any]]]:
    """
    Python port of @n8n/utils sublimeSearch.
    Returns [(score, node), ...] sorted descending, score > 0 only.
    """
    q = query.strip().lower()
    if not q:
        return []

    scored: List[Tuple[float, Dict]] = []
    for node in nodes:
        total = sum(
            _field_score(q, _get_field_value(node, sk["key"]), sk["weight"])
            for sk in search_keys
        )
        if total > 0:
            scored.append((total, node))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

#
# dedupeNodes  (port of n8n dedupeNodes — keeps latest version)#
def _get_latest_version(node: Dict[str, Any]) -> int:
    v = node.get("version", 1)
    return max(v) if isinstance(v, list) else int(v)


def dedupe_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only the latest version of each node name."""
    cache: Dict[str, Dict[str, Any]] = {}
    for node in nodes:
        name = node.get("name", "")
        cached = cache.get(name)
        if not cached or _get_latest_version(node) > _get_latest_version(cached):
            cache[name] = node
    return list(cache.values())

#
# NodeSearchEngine#
class NodeSearchEngine:

    def __init__(self, node_types: List[Dict[str, Any]]):
        # Deduplicate — always keep latest version (n8n pattern)
        self.node_types = dedupe_nodes(node_types)
        # Fast lookup: name → node
        self._by_name: Dict[str, Dict[str, Any]] = {
            n.get("name", ""): n for n in self.node_types
        }

    # ── searchByName ─────────────────────────────────────────────
    def search_by_name(self, query: str, limit: int = 5) -> List[NodeSearchResult]:
        """Fuzzy search using sublimeSearch across all node fields."""
        results = sublime_search(query, self.node_types, NODE_SEARCH_KEYS)
        return [self._to_result(node, score) for score, node in results[:limit]]

    # ── searchByNodeType ─────────────────────────────────────────
    def search_by_node_type(
        self,
        node_type: str,        # "trigger" | "action" | "conditional"
        limit: int = 10,
    ) -> List[NodeSearchResult]:
        """Return all nodes of a given nodeType."""
        t = node_type.lower().strip()
        matches = [n for n in self.node_types if n.get("nodeType", "").lower() == t]
        return [self._to_result(n, 100.0) for n in matches[:limit]]

    # ── formatResult  (port of n8n formatResult) ─────────────────
    def format_result(self, result: NodeSearchResult) -> str:
        """XML-like string — same structure as n8n formatResult()."""
        return (
            f"\n\t<node>"
            f"\n\t\t<node_name>{result.name}</node_name>"
            f"\n\t\t<node_type>{result.node_type}</node_type>"
            f"\n\t\t<node_description>{result.description}</node_description>"
            f"\n\t</node>"
        )

    # ── resolve_node_type ─────────────────────────────────────────
    def resolve_node_type(self, requested: str) -> Tuple[str, str]:
        """
        Map whatever the LLM says to a real node name.

        Resolution order:
        1. Exact match            → "HTTP REQUEST" == "HTTP REQUEST"
        2. Case-insensitive exact → "http request" → "HTTP REQUEST"
        3. sublimeSearch top hit  → fuzzy best match
        4. Hard fallback          → "HTTP REQUEST"
        """
        req = requested.strip()

        # 1. Exact
        if req in self._by_name:
            return req, f"Exact match: {req}"

        # 2. Case-insensitive
        req_lower = req.lower()
        for name in self._by_name:
            if name.lower() == req_lower:
                return name, f"Case-insensitive match: '{req}' → '{name}'"

        # 3. sublimeSearch
        results = self.search_by_name(req, limit=1)
        if results:
            return results[0].name, (
                f"sublimeSearch: '{req}' → '{results[0].name}' "
                f"(score={results[0].score:.2f})"
            )

        # 4. Fallback
        fallback = "HTTP REQUEST"
        return fallback, f"No match for '{req}', falling back to '{fallback}'"

    # ── get_node_details ──────────────────────────────────────────
    def get_node_details(self, node_name: str, version: int = 1) -> Optional[NodeDetails]:
        node = self._by_name.get(node_name)
        if not node:
            # Try case-insensitive
            node = next(
                (n for n in self.node_types if n.get("name", "").lower() == node_name.lower()),
                None,
            )
        if not node:
            return None
        return NodeDetails(
            name=node.get("name", ""),
            display_name=node.get("displayName", ""),
            description=node.get("description", ""),
            properties=node.get("properties", []),
            inputs=[],
            outputs=[],
            version=_get_latest_version(node),
        )

    # ── get_all_node_names ────────────────────────────────────────
    def get_all_node_names(self) -> List[Dict[str, str]]:
        """Compact listing for LLM context — grouped by nodeType."""
        return [
            {
                "name":        n.get("name", ""),
                "displayName": n.get("displayName", ""),
                "nodeType":    n.get("nodeType", ""),
                "description": n.get("description", ""),
                "aliases":     ", ".join(n.get("codex", {}).get("alias", [])),
            }
            for n in self.node_types
        ]

    # ── internal ──────────────────────────────────────────────────
    def _to_result(self, node: Dict[str, Any], score: float) -> NodeSearchResult:
        return NodeSearchResult(
            name=node.get("name", ""),
            display_name=node.get("displayName", ""),
            description=node.get("description", "No description"),
            version=_get_latest_version(node),
            inputs=[],     # not used in 3-type model
            outputs=[],    # not used in 3-type model
            score=score,
            node_type=node.get("nodeType", "action"),
        )