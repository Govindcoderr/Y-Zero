# engines/node_search_engine.py
from typing import List, Optional, Dict, Any
from ..types.nodes import NodeSearchResult, NodeDetails
import re

class NodeSearchEngine:
    def __init__(self, node_types: List[Dict[str, Any]]):
        self.node_types = node_types
        self._build_index()
    
    def _build_index(self):
        """Build search index for faster lookups"""
        self.name_index = {}
        self.keyword_index = {}
        
        for node in self.node_types:
            name = node.get("name", "").lower()
            display_name = node.get("displayName", "").lower()
            description = node.get("description", "").lower()
            
            # Index by name
            self.name_index[name] = node
            
            # Index keywords
            keywords = set(name.split(".") + display_name.split() + description.split())
            for keyword in keywords:
                if len(keyword) > 2:
                    if keyword not in self.keyword_index:
                        self.keyword_index[keyword] = []
                    self.keyword_index[keyword].append(node)
    
    def search_by_name(self, query: str, limit: int = 10) -> List[NodeSearchResult]:
        """Search nodes by name or description"""
        query_lower = query.lower()
        results = []
        
        for node_type in self.node_types:
            score = 0.0
            name = node_type.get("name", "").lower()
            display_name = node_type.get("displayName", "").lower()
            description = node_type.get("description", "").lower()
            
            # Exact name match
            if query_lower == name:
                score += 100
            elif query_lower in name:
                score += 80
            
            # Display name match
            if query_lower == display_name:
                score += 90
            elif query_lower in display_name:
                score += 70
            
            # Description match
            if query_lower in description:
                score += 50
            
            # Keyword match
            query_words = query_lower.split()
            for word in query_words:
                if word in name:
                    score += 20
                if word in display_name:
                    score += 15
                if word in description:
                    score += 10
            
            if score > 0:
                results.append(NodeSearchResult(
                    name=node_type.get("name", ""),
                    display_name=node_type.get("displayName", ""),
                    description=node_type.get("description", "No description"),
                    version=self._get_latest_version(node_type),
                    inputs=node_type.get("inputs", []),
                    outputs=node_type.get("outputs", []),
                    score=score
                ))
        
        # Sort by score and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def _get_latest_version(self, node_type: Dict[str, Any]) -> int:
        """Get latest version of a node type"""
        version = node_type.get("version", 1)
        if isinstance(version, list):
            return max(version)
        return version
    
    def get_node_details(self, node_name: str, version: int) -> Optional[NodeDetails]:
        """Get detailed information about a specific node"""
        node_type = next(
            (nt for nt in self.node_types 
             if nt.get("name") == node_name and self._matches_version(nt, version)),
            None
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
            version=self._get_latest_version(node_type)
        )
    
    def _matches_version(self, node_type: Dict[str, Any], version: int) -> bool:
        """Check if node type matches version"""
        node_version = node_type.get("version", 1)
        if isinstance(node_version, list):
            return version in node_version
        return node_version == version
    
    def search_by_category(self, category: str) -> List[NodeSearchResult]:
        """Search nodes by category or group"""
        category_lower = category.lower()
        results = []
        
        for node_type in self.node_types:
            groups = node_type.get("group", [])
            if isinstance(groups, str):
                groups = [groups]
            
            if any(category_lower in g.lower() for g in groups):
                results.append(NodeSearchResult(
                    name=node_type.get("name", ""),
                    display_name=node_type.get("displayName", ""),
                    description=node_type.get("description", "No description"),
                    version=self._get_latest_version(node_type),
                    inputs=node_type.get("inputs", []),
                    outputs=node_type.get("outputs", []),
                    score=100
                ))
        
        return results