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
from typing import List, Optional, Dict, Any, Tuple
from ..types.nodes import NodeSearchResult, NodeDetails


# Semantic aliases: maps intent keywords → preferred node type names in the JSON.
# If the exact node isn't in the file, the engine falls back to similarity scoring.
SEMANTIC_ALIASES = {
    # Messaging / notifications
    "whatsapp":     ["workflow.httpRequest"],   # use HTTP Request + Twilio API
    "telegram":     ["workflow.httpRequest"],
    "sms":          ["workflow.httpRequest"],
    "twilio":       ["workflow.httpRequest"],
    "push":         ["workflow.httpRequest"],
    "notify":       ["workflow.emailSend", "workflow.slack", "workflow.httpRequest"],
    "notification": ["workflow.emailSend", "workflow.slack", "workflow.httpRequest"],
    "alert":        ["workflow.emailSend", "workflow.slack", "workflow.httpRequest"],
    "message":      ["workflow.slack", "workflow.emailSend", "workflow.httpRequest"],
    "msg":          ["workflow.slack", "workflow.emailSend", "workflow.httpRequest"],
    # Scheduling
    "cron":         ["workflow.scheduleTrigger"],
    "schedule":     ["workflow.scheduleTrigger"],
    "timer":        ["workflow.scheduleTrigger"],
    "interval":     ["workflow.scheduleTrigger"],
    "daily":        ["workflow.scheduleTrigger"],
    "hourly":       ["workflow.scheduleTrigger"],
    "weekly":       ["workflow.scheduleTrigger"],
    # HTTP / API
    "api":          ["workflow.httpRequest"],
    "http":         ["workflow.httpRequest"],
    "rest":         ["workflow.httpRequest"],
    "fetch":        ["workflow.httpRequest"],
    "request":      ["workflow.httpRequest"],
    "get":          ["workflow.httpRequest"],
    "post":         ["workflow.httpRequest"],
    "webhook":      ["workflow.webhook"],
    # Data
    "transform":    ["workflow.set", "workflow.code"],
    "extract":      ["workflow.set", "workflow.code"],
    "parse":        ["workflow.set", "workflow.code"],
    "map":          ["workflow.set"],
    "set":          ["workflow.set"],
    "filter":       ["workflow.if"],
    "condition":    ["workflow.if"],
    "branch":       ["workflow.if"],
    "if":           ["workflow.if"],
    "check":        ["workflow.if"],
    "code":         ["workflow.code"],
    "script":       ["workflow.code"],
    "python":       ["workflow.code"],
    "javascript":   ["workflow.code"],
    # Email
    "email":        ["workflow.emailSend"],
    "mail":         ["workflow.emailSend"],
    "smtp":         ["workflow.emailSend"],
    "send":         ["workflow.emailSend", "workflow.slack", "workflow.httpRequest"],
    # Chat
    "slack":        ["workflow.slack"],
    "discord":      ["workflow.httpRequest"],
    "teams":        ["workflow.httpRequest"],
}


class NodeSearchEngine:
    def __init__(self, node_types: List[Dict[str, Any]]):
        self.node_types = node_types
        # Build a quick lookup set of all valid node names
        self.valid_names = {nt.get("name", "") for nt in node_types}
        self._build_index()

    def _build_index(self):
        """Build search index for faster lookups"""
        self.name_index: Dict[str, Dict] = {}
        self.keyword_index: Dict[str, List[Dict]] = {}

        for node in self.node_types:
            name = node.get("name", "").lower()
            display_name = node.get("displayName", "").lower()
            description = node.get("description", "").lower()

            self.name_index[name] = node

            keywords = set(name.split(".") + display_name.split() + description.split())
            for keyword in keywords:
                if len(keyword) > 2:
                    if keyword not in self.keyword_index:
                        self.keyword_index[keyword] = []
                    self.keyword_index[keyword].append(node)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_node_type(self, requested: str) -> Tuple[str, str]:
        """
        Given a node type name the LLM wants to use, return:
          (actual_node_name, explanation)

        Logic:
        1. Exact match in JSON → use it directly.
        2. Semantic alias match → return best available alias.
        3. Keyword similarity search → return highest scoring result.
        4. Nothing found → return workflow.httpRequest as universal fallback.
        """
        req_lower = requested.lower().strip()

        # 1. Exact match
        if requested in self.valid_names:
            return requested, f"Exact match found: {requested}"

        # 2. Partial name match (e.g. "scheduleTrigger" → "workflow.scheduleTrigger")
        for valid in self.valid_names:
            if req_lower in valid.lower() or valid.lower() in req_lower:
                return valid, f"Partial name match: '{requested}' → '{valid}'"

        # 3. Semantic alias lookup
        for keyword, candidates in SEMANTIC_ALIASES.items():
            if keyword in req_lower:
                for candidate in candidates:
                    if candidate in self.valid_names:
                        return candidate, (
                            f"'{requested}' not in node list. "
                            f"Semantic alias '{keyword}' → using '{candidate}'"
                        )

        # 4. Keyword similarity search across all node metadata
        results = self.search_by_name(req_lower, limit=1)
        if results:
            return results[0].name, (
                f"'{requested}' not in node list. "
                f"Best similarity match → '{results[0].name}' ({results[0].display_name})"
            )

        # 5. Universal fallback
        fallback = "workflow.httpRequest"
        if fallback in self.valid_names:
            return fallback, (
                f"'{requested}' not found and no similar node detected. "
                f"Falling back to '{fallback}' (generic HTTP Request)."
            )

        # Last resort: return first node in list
        first = self.node_types[0].get("name", "")
        return first, f"No match found for '{requested}', using first available: '{first}'"

    def get_all_node_names(self) -> List[Dict[str, str]]:
        """Return a compact list of all available nodes for LLM context."""
        return [
            {
                "name": nt.get("name", ""),
                "displayName": nt.get("displayName", ""),
                "description": nt.get("description", ""),
                "group": nt.get("group", []),
            }
            for nt in self.node_types
        ]

    def search_by_name(self, query: str, limit: int = 10) -> List[NodeSearchResult]:
        """Search nodes by name or description"""
        query_lower = query.lower()
        results = []

        for node_type in self.node_types:
            score = 0.0
            name = node_type.get("name", "").lower()
            display_name = node_type.get("displayName", "").lower()
            description = node_type.get("description", "").lower()
            groups = " ".join(node_type.get("group", []))

            if query_lower == name:
                score += 100
            elif query_lower in name:
                score += 80

            if query_lower == display_name:
                score += 90
            elif query_lower in display_name:
                score += 70

            if query_lower in description:
                score += 50

            if query_lower in groups:
                score += 40

            query_words = query_lower.split()
            for word in query_words:
                if len(word) < 3:
                    continue
                if word in name:
                    score += 20
                if word in display_name:
                    score += 15
                if word in description:
                    score += 10
                if word in groups:
                    score += 8

            if score > 0:
                results.append(
                    NodeSearchResult(
                        name=node_type.get("name", ""),
                        display_name=node_type.get("displayName", ""),
                        description=node_type.get("description", "No description"),
                        version=self._get_latest_version(node_type),
                        inputs=node_type.get("inputs", []),
                        outputs=node_type.get("outputs", []),
                        score=score,
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _get_latest_version(self, node_type: Dict[str, Any]) -> int:
        version = node_type.get("version", 1)
        if isinstance(version, list):
            return max(version)
        return version

    def get_node_details(self, node_name: str, version: int = 1) -> Optional[NodeDetails]:
        # Exact + version match
        node_type = next(
            (
                nt
                for nt in self.node_types
                if nt.get("name") == node_name and self._matches_version(nt, version)
            ),
            None,
        )
        # Fallback: name only
        if not node_type:
            node_type = next(
                (nt for nt in self.node_types if nt.get("name") == node_name), None
            )
        if not node_type:
            return None

        return NodeDetails(
            name=node_type.get("name", ""),
            display_name=node_type.get("displayName", ""),
            description=node_type.get("description", "No description"),
            properties=node_type.get("properties", []),
            inputs=node_type.get("inputs", []),
            outputs=node_type.get("outputs", []),
            version=self._get_latest_version(node_type),
        )

    def _matches_version(self, node_type: Dict[str, Any], version: int) -> bool:
        node_version = node_type.get("version", 1)
        if isinstance(node_version, list):
            return version in node_version
        return node_version == version

    def search_by_category(self, category: str) -> List[NodeSearchResult]:
        category_lower = category.lower()
        results = []
        for node_type in self.node_types:
            groups = node_type.get("group", [])
            if isinstance(groups, str):
                groups = [groups]
            if any(category_lower in g.lower() for g in groups):
                results.append(
                    NodeSearchResult(
                        name=node_type.get("name", ""),
                        display_name=node_type.get("displayName", ""),
                        description=node_type.get("description", "No description"),
                        version=self._get_latest_version(node_type),
                        inputs=node_type.get("inputs", []),
                        outputs=node_type.get("outputs", []),
                        score=100,
                    )
                )
        return results