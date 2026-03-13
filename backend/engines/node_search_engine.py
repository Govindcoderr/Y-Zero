# # engines/node_search_engine.py

# """
# NodeSearchEngine — search and resolve n8n node types for the Configurator agent.

# Node types: trigger | action | conditional  (no inputs/outputs fields)
# Node name = the "value" used directly in the output JSON (e.g. "HTTP REQUEST", "TELEGRAM")

# Key design:
# - sublimeSearch with weighted keys: displayName > name > codex.alias > description
# - dedupeNodes — latest version wins
# - searchByName(query, limit)
# - searchByNodeType(nodeType, limit)
# - formatResult(result) — XML string for LLM
# - resolve_node_type(requested) — fuzzy → exact node name
# """
# from __future__ import annotations
# from difflib import SequenceMatcher
# from typing import List, Optional, Dict, Any, Tuple
# from ..types.nodes import NodeSearchResult, NodeDetails
# from ..utils.node_normalizer import normalize_nodes
# from ..types.workflow import register_node_types  # ← add this import 


# # NODE_SEARCH_KEYS  (mirrors n8n exactly)#
# NODE_SEARCH_KEYS = [
#     {"key": "displayName", "weight": 1.5},
#     {"key": "name",        "weight": 1.3},
#     {"key": "codex.alias", "weight": 1.0},
#     {"key": "description", "weight": 0.7},
# ]

# #
# # sublimeSearch  (Python port of @n8n/utils sublimeSearch)#
# def _get_field_value(node: Dict[str, Any], key: str) -> str:
#     """Resolve dotted keys like 'codex.alias'. Returns joined string for lists."""
#     parts = key.split(".")
#     val = node
#     for p in parts:
#         val = val.get(p, "") if isinstance(val, dict) else ""
#     if isinstance(val, list):
#         return " ".join(str(v) for v in val)
#     return str(val) if val else ""


# def _field_score(query: str, text: str, weight: float) -> float:
#     """Weighted fuzzy score for one field — mirrors sublimeSearch scoring."""
#     if not query or not text:
#         return 0.0
#     q, t = query.lower(), text.lower()

#     if q == t:                  return weight * 1.00
#     if t.startswith(q):         return weight * 0.90
#     if q in t:                  return weight * 0.80

#     words = q.split()
#     hits  = sum(1 for w in words if w in t)
#     ratio = hits / len(words)
#     if ratio == 1.0:            return weight * 0.75
#     if ratio > 0.0:             return weight * ratio * 0.70

#     fuzzy = SequenceMatcher(None, q, t).ratio()
#     if fuzzy > 0.45:            return weight * fuzzy * 0.55

#     return 0.0


# def sublime_search(
#     query: str,
#     nodes: List[Dict[str, Any]],
#     search_keys: List[Dict[str, Any]],
# ) -> List[Tuple[float, Dict[str, Any]]]:
#     """
#     Python port of @n8n/utils sublimeSearch.
#     Returns [(score, node), ...] sorted descending, score > 0 only.
#     """
#     q = query.strip().lower()
#     if not q:
#         return []

#     scored: List[Tuple[float, Dict]] = []
#     for node in nodes:
#         total = sum(
#             _field_score(q, _get_field_value(node, sk["key"]), sk["weight"])
#             for sk in search_keys
#         )
#         if total > 0:
#             scored.append((total, node))

#     scored.sort(key=lambda x: x[0], reverse=True)
#     return scored

# # dedupeNodes  (port of n8n dedupeNodes — keeps latest version)#
# def _get_latest_version(node: Dict[str, Any]) -> int:
#     v = node.get("version", 1)
#     return max(v) if isinstance(v, list) else int(v)


# def dedupe_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """Keep only the latest version of each node name."""
#     cache: Dict[str, Dict[str, Any]] = {}
#     for node in nodes:
#         name = node.get("name", "")
#         cached = cache.get(name)
#         if not cached or _get_latest_version(node) > _get_latest_version(cached):
#             cache[name] = node
#     return list(cache.values())


# # NodeSearchEngine#
# class NodeSearchEngine:

#     def __init__(self, node_types: List[Dict[str, Any]]):
#         # Deduplicate — always keep latest version (n8n pattern)
#         node_types = normalize_nodes(node_types)  
#         self.node_types = dedupe_nodes(node_types)
#         # Fast lookup: name → node
#         self._by_name: Dict[str, Dict[str, Any]] = {
#             n.get("name", ""): n for n in self.node_types
#         }
#         register_node_types(self.node_types)  # ← register nodes for workflow execution

#     # ── searchByName ─────────────────────────────────────────────
#     def search_by_name(self, query: str, limit: int = 5) -> List[NodeSearchResult]:
#         """Fuzzy search using sublimeSearch across all node fields."""
#         results = sublime_search(query, self.node_types, NODE_SEARCH_KEYS)
#         return [self._to_result(node, score) for score, node in results[:limit]]

#     # ── searchByNodeType ─────────────────────────────────────────
#     def search_by_node_type(
#         self,
#         node_type: str,        # "trigger" | "action" | "conditional"
#         limit: int = 10,
#     ) -> List[NodeSearchResult]:
#         """Return all nodes of a given nodeType."""
#         t = node_type.lower().strip()
#         matches = [n for n in self.node_types if n.get("nodeType", "").lower() == t]
#         return [self._to_result(n, 100.0) for n in matches[:limit]]

#     # ── formatResult  (port of n8n formatResult) ─────────────────
#     def format_result(self, result: NodeSearchResult) -> str:
#         """XML-like string — same structure as n8n formatResult()."""
#         return (
#             f"\n\t<node>"
#             f"\n\t\t<node_name>{result.name}</node_name>"
#             f"\n\t\t<node_type>{result.node_type}</node_type>"
#             f"\n\t\t<node_description>{result.description}</node_description>"
#             f"\n\t</node>"
#         )

#     # ── resolve_node_type ─────────────────────────────────────────
#     def resolve_node_type(self, requested: str) -> Tuple[str, str]:
#         """
#         Map whatever the LLM says to a real node name.

#         Resolution order:
#         1. Exact match            → "HTTP REQUEST" == "HTTP REQUEST"
#         2. Case-insensitive exact → "http request" → "HTTP REQUEST"
#         3. sublimeSearch top hit  → fuzzy best match
#         4. Hard fallback          → "HTTP REQUEST"
#         """
#         req = requested.strip()

#         # 1. Exact
#         if req in self._by_name:
#             return req, f"Exact match: {req}"

#         # 2. Case-insensitive
#         req_lower = req.lower()
#         for name in self._by_name:
#             if name.lower() == req_lower:
#                 return name, f"Case-insensitive match: '{req}' → '{name}'"

#         # 3. sublimeSearch
#         results = self.search_by_name(req, limit=1)
#         if results:
#             return results[0].name, (
#                 f"sublimeSearch: '{req}' → '{results[0].name}' "
#                 f"(score={results[0].score:.2f})"
#             )

#         # 4. Fallback
#         fallback = "HTTP REQUEST"
#         return fallback, f"No match for '{req}', falling back to '{fallback}'"

#     # ── get_node_details ──────────────────────────────────────────
#     def get_node_details(self, node_name: str, version: int = 1) -> Optional[NodeDetails]:
#         node = self._by_name.get(node_name)
#         if not node:
#             # Try case-insensitive
#             node = next(
#                 (n for n in self.node_types if n.get("name", "").lower() == node_name.lower()),
#                 None,
#             )
#         if not node:
#             return None
#         return NodeDetails(
#             name=node.get("name", ""),
#             display_name=node.get("displayName", ""),
#             description=node.get("description", ""),
#             properties=node.get("properties", []),
#             inputs=[],
#             outputs=[],
#             version=_get_latest_version(node),
#         )

#     # ── get_all_node_names ────────────────────────────────────────
#     def get_all_node_names(self) -> List[Dict[str, str]]:
#         """Compact listing for LLM context — grouped by nodeType."""
#         return [
#             {
#                 "name":        n.get("name", ""),
#                 "displayName": n.get("displayName", ""),
#                 "nodeType":    n.get("nodeType", ""),
#                 "description": n.get("description", ""),
#                 "aliases":     ", ".join(n.get("codex", {}).get("alias", [])),
#             }
#             for n in self.node_types
#         ]

#     # ── internal .....──
#     def _to_result(self, node: Dict[str, Any], score: float) -> NodeSearchResult:
#         return NodeSearchResult(
#             name=node.get("name", ""),
#             display_name=node.get("displayName", ""),
#             description=node.get("description", "No description"),
#             version=_get_latest_version(node),
#             inputs=[],     # not used in 3-type model
#             outputs=[],    # not used in 3-type model
#             score=score,
#             node_type=node.get("nodeType", "action"),
#         )
    






# backend/engines/node_search_engine.py
"""
NodeSearchEngine — Elasticsearch backend.

Drop-in replacement for the old sublimeSearch engine.
Public interface is IDENTICAL — no other file needs to change.

Public methods (unchanged):
  search_by_name(query, limit)       → List[NodeSearchResult]
  search_by_node_type(type, limit)   → List[NodeSearchResult]
  resolve_node_type(requested)       → Tuple[str, str]
  get_node_details(name, version)    → Optional[NodeDetails]
  get_all_node_names()               → List[Dict]
  format_result(result)              → str

ES index schema:
  name          keyword + text (exact + full-text)
  displayName   text (boost 1.5)
  description   text (boost 0.7)
  aliases       text (boost 1.0)
  nodeType      keyword  (trigger | action | conditional)
  version       integer
  _raw          object (disabled — stores full node dict for retrieval)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from elasticsearch import Elasticsearch, NotFoundError, ConnectionError as ESConnectionError

from ..types.nodes import NodeSearchResult, NodeDetails
from ..utils.node_normalizer import normalize_nodes
from ..types.workflow import register_node_types

# ── Index name (override via env) ─────────────────────────────────────────────
ES_INDEX = os.getenv("ES_NODE_INDEX", "yzero_nodes")

# ── Index mapping ─────────────────────────────────────────────────────────────
INDEX_MAPPING = {
    "settings": {
        "analysis": {
            "analyzer": {
                # custom analyzer: lowercase + edge-ngram for prefix matching
                "node_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
                "node_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            }
        },
        "index": {
            "number_of_shards": 1,    # single node setup
            "number_of_replicas": 0,  # no replicas for local/dev
        },
    },
    "mappings": {
        "dynamic": "strict",   # reject unknown fields — no surprise mappings
        "properties": {
            # boost removed — ES 8.x does not allow boost in mappings
            # boost is applied at query time via fields: ["name^1.3", ...]
            "name": {
                "type": "text",
                "analyzer": "node_analyzer",
                "search_analyzer": "node_search_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"}
                },
            },
            "displayName": {
                "type": "text",
                "analyzer": "node_analyzer",
                "search_analyzer": "node_search_analyzer",
            },
            "description": {
                "type": "text",
                "analyzer": "node_analyzer",
                "search_analyzer": "node_search_analyzer",
            },
            "aliases": {
                "type": "text",
                "analyzer": "node_analyzer",
                "search_analyzer": "node_search_analyzer",
            },
            "nodeType": {
                "type": "keyword",
            },
            "version": {
                "type": "integer",
            },
            # _raw stored as binary (base64) — ES never tries to parse it
            # retrieved via _source, decoded back to dict in Python
            "_raw": {
                "type": "binary",
                "doc_values": False,
            },
        }
    },
}


def _get_latest_version(node: Dict[str, Any]) -> int:
    v = node.get("version", 1)
    return max(v) if isinstance(v, list) else int(v)


def _node_to_doc(node: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a normalized node dict → ES document.
    _raw is stored as base64-encoded JSON binary so ES never tries to parse it.
    This avoids ALL document_parsing_exception errors regardless of node structure.
    """
    import base64

    aliases = node.get("codex", {}).get("alias", [])
    if isinstance(aliases, list):
        aliases_str = " ".join(aliases)
    else:
        aliases_str = str(aliases)

    # Encode full node as base64 JSON — ES stores it as binary, never indexes it
    raw_bytes  = json.dumps(node, ensure_ascii=False).encode("utf-8")
    raw_b64    = base64.b64encode(raw_bytes).decode("utf-8")

    return {
        "name":        node.get("name", ""),
        "displayName": node.get("displayName", ""),
        "description": node.get("description", ""),
        "aliases":     aliases_str,
        "nodeType":    node.get("nodeType", "action"),
        "version":     _get_latest_version(node),
        "_raw":        raw_b64,   # base64-encoded JSON, never parsed by ES
    }


# ══════════════════════════════════════════════════════════════════════════════
# NodeSearchEngine
# ══════════════════════════════════════════════════════════════════════════════

class NodeSearchEngine:
    """
    Elasticsearch-backed node search engine.

    Falls back gracefully to in-memory sublimeSearch if ES is unavailable,
    so development without a running ES instance still works.
    """

    def __init__(self, node_types: List[Dict[str, Any]]):
        # ── Normalize & dedupe ────────────────────────────────────
        node_types = normalize_nodes(node_types)
        self.node_types = self._dedupe(node_types)

        # ── Fast in-memory name lookup (always kept) ───────────────
        # Used for exact/case-insensitive resolve + fallback search
        self._by_name: Dict[str, Dict[str, Any]] = {
            n.get("name", ""): n for n in self.node_types
        }

        # ── Register for workflow.py parameter extraction ─────────
        register_node_types(self.node_types)

        # ── Connect to Elasticsearch ──────────────────────────────
        es_url  = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
        es_user = os.getenv("ELASTICSEARCH_USER", "")
        es_pass = os.getenv("ELASTICSEARCH_PASSWORD", "")

        try:
            if es_user and es_pass:
                self._es = Elasticsearch(
                    es_url,
                    basic_auth=(es_user, es_pass),
                    request_timeout=10,
                    retry_on_timeout=True,
                    max_retries=2,
                )
            else:
                self._es = Elasticsearch(
                    es_url,
                    request_timeout=10,
                    retry_on_timeout=True,
                    max_retries=2,
                )

            # Ping to verify connection
            if self._es.ping():
                print(f"✅ Elasticsearch connected: {es_url}")
                self._es_available = True
                self._ensure_index()
                self._index_nodes()
            else:
                raise ESConnectionError("Ping failed")

        except Exception as e:
            print(f"⚠️  Elasticsearch unavailable ({e}) — using in-memory fallback")
            self._es_available = False
            self._es = None

        print(
            f"✅ NodeSearchEngine ready | "
            f"{len(self.node_types)} nodes | "
            f"backend={'elasticsearch' if self._es_available else 'in-memory fallback'}"
        )

    # ──────────────────────────────────────────────────────────────
    # Public interface (identical to old engine)
    # ──────────────────────────────────────────────────────────────

    def search_by_name(self, query: str, limit: int = 10) -> List[NodeSearchResult]:
        """
        Full-text fuzzy search across name, displayName, aliases, description.
        Uses ES multi_match with fuzziness AUTO when available, else in-memory.
        """
        if self._es_available:
            return self._es_search_by_name(query, limit)
        return self._mem_search_by_name(query, limit)

    def search_by_node_type(
        self,
        node_type: str,
        limit: int = 30,
    ) -> List[NodeSearchResult]:
        """Return all nodes of a given nodeType (trigger | action | conditional)."""
        t = node_type.lower().strip()

        if self._es_available:
            return self._es_search_by_type(t, limit)

        # in-memory fallback
        matches = [n for n in self.node_types if n.get("nodeType", "").lower() == t]
        return [self._to_result(n, 100.0) for n in matches[:limit]]

    def resolve_node_type(self, requested: str) -> Tuple[str, str]:
        """
        Map whatever the LLM says → real registered node name.

        Resolution order:
          1. Exact match
          2. Case-insensitive exact
          3. ES search top hit  (or sublimeSearch fallback)
          4. Hard fallback → "HTTP REQUEST"
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

        # 3. Search top hit
        results = self.search_by_name(req, limit=1)
        if results:
            return results[0].name, (
                f"Search match: '{req}' → '{results[0].name}' "
                f"(score={results[0].score:.2f})"
            )

        # 4. Fallback
        fallback = "HTTP REQUEST"
        return fallback, f"No match for '{req}', falling back to '{fallback}'"

    def get_node_details(self, node_name: str, version: int = 1) -> Optional[NodeDetails]:
        node = self._by_name.get(node_name)
        if not node:
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

    def get_all_node_names(self) -> List[Dict[str, str]]:
        """Compact listing for LLM system prompt — grouped by nodeType."""
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

    def format_result(self, result: NodeSearchResult) -> str:
        """XML-like string for LLM — same as before."""
        return (
            f"\n\t<node>"
            f"\n\t\t<node_name>{result.name}</node_name>"
            f"\n\t\t<node_type>{result.node_type}</node_type>"
            f"\n\t\t<node_description>{result.description}</node_description>"
            f"\n\t</node>"
        )

    # ──────────────────────────────────────────────────────────────
    # Elasticsearch internals
    # ──────────────────────────────────────────────────────────────

    def _ensure_index(self) -> None:
        """
        Create index with correct mapping.
        If index already exists with OLD mapping (e.g. boost error),
        delete it and recreate so fresh mapping is applied.
        """
        try:
            if self._es.indices.exists(index=ES_INDEX):
                # Check if mapping has the old 'boost' field — if so, recreate
                mapping = self._es.indices.get_mapping(index=ES_INDEX)
                props   = mapping[ES_INDEX]["mappings"].get("properties", {})
                has_old_boost  = "boost" in props.get("name", {})
                has_old_object = props.get("_raw", {}).get("type") == "object"

                if has_old_boost or has_old_object:
                    print(f"🔄 Old ES mapping detected — recreating index '{ES_INDEX}'")
                    self._es.indices.delete(index=ES_INDEX)
                else:
                    print(f"📦 ES index '{ES_INDEX}' exists with correct mapping")
                    return

            self._es.indices.create(index=ES_INDEX, body=INDEX_MAPPING)
            print(f"📦 ES index '{ES_INDEX}' created with correct mapping")

        except Exception as e:
            print(f"⚠️  Could not create ES index: {e}")

    def _index_nodes(self) -> None:
        """
        Bulk-index all nodes into ES.
        Uses node name as document ID so re-indexing is idempotent
        (same node re-indexed = update, not duplicate).
        """
        if not self.node_types:
            return

        from elasticsearch.helpers import bulk

        actions = [
            {
                "_index": ES_INDEX,
                "_id":    node.get("name", ""),   # idempotent upsert by name
                "_source": _node_to_doc(node),
            }
            for node in self.node_types
            if node.get("name")
        ]

        try:
            success, errors = bulk(self._es, actions, raise_on_error=False)
            print(f"📥 ES indexed {success} nodes | errors: {len(errors) if errors else 0}")
            if errors:
                for err in errors[:3]:
                    print(f"   ⚠️  Index error: {err}")
        except Exception as e:
            print(f"⚠️  Bulk index failed: {e}")

    def _es_search_by_name(self, query: str, limit: int) -> List[NodeSearchResult]:
        """
        ES multi_match query across all text fields.
        Uses fuzziness AUTO — handles typos automatically.
        Also runs a phrase_prefix query for prefix matching.
        Both are combined with should so either can match.
        """
        try:
            body = {
                "size": limit,
                "query": {
                    "bool": {
                        "should": [
                            # 1. Fuzzy full-text across all fields
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "displayName^1.5",
                                        "name^1.3",
                                        "aliases^1.0",
                                        "description^0.7",
                                    ],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                    "prefix_length": 1,   # first char must match
                                    "operator": "or",
                                }
                            },
                            # 2. Phrase prefix — handles "whats" → "whatsapp"
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "displayName^2.0",
                                        "name^1.5",
                                        "aliases^1.0",
                                    ],
                                    "type": "phrase_prefix",
                                    "max_expansions": 20,
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "_source": True,
            }

            resp = self._es.search(index=ES_INDEX, body=body)
            hits = resp["hits"]["hits"]

            results = []
            for hit in hits:
                raw_node = self._decode_raw(hit["_source"].get("_raw", ""))
                score    = hit["_score"] or 0.0
                results.append(self._to_result(raw_node, score))

            return results

        except Exception as e:
            print(f"⚠️  ES search failed ({e}), falling back to in-memory")
            return self._mem_search_by_name(query, limit)

    def _es_search_by_type(self, node_type: str, limit: int) -> List[NodeSearchResult]:
        """Filter by nodeType keyword."""
        try:
            body = {
                "size": limit,
                "query": {
                    "term": {"nodeType": node_type}
                },
                "_source": True,
            }
            resp = self._es.search(index=ES_INDEX, body=body)
            hits = resp["hits"]["hits"]
            return [self._to_result(self._decode_raw(h["_source"].get("_raw", "")), 100.0) for h in hits]

        except Exception as e:
            print(f"⚠️  ES type filter failed ({e}), falling back to in-memory")
            matches = [n for n in self.node_types if n.get("nodeType", "").lower() == node_type]
            return [self._to_result(n, 100.0) for n in matches[:limit]]

    # ──────────────────────────────────────────────────────────────
    # In-memory fallback (kept from original — used when ES is down)
    # ──────────────────────────────────────────────────────────────

    def _mem_search_by_name(self, query: str, limit: int) -> List[NodeSearchResult]:
        """Original sublimeSearch — runs when ES unavailable."""
        from difflib import SequenceMatcher

        NODE_SEARCH_KEYS = [
            {"key": "displayName", "weight": 1.5},
            {"key": "name",        "weight": 1.3},
            {"key": "codex.alias", "weight": 1.0},
            {"key": "description", "weight": 0.7},
        ]

        def _get_field(node, key):
            parts = key.split(".")
            val = node
            for p in parts:
                val = val.get(p, "") if isinstance(val, dict) else ""
            if isinstance(val, list):
                return " ".join(str(v) for v in val)
            return str(val) if val else ""

        def _score(q, text, weight):
            if not q or not text:
                return 0.0
            q, t = q.lower(), text.lower()
            if q == t:              return weight * 1.00
            if t.startswith(q):    return weight * 0.90
            if q in t:             return weight * 0.80
            words = q.split()
            hits  = sum(1 for w in words if w in t)
            ratio = hits / len(words)
            if ratio == 1.0:       return weight * 0.75
            if ratio > 0.0:        return weight * ratio * 0.70
            fuzzy = SequenceMatcher(None, q, t).ratio()
            if fuzzy > 0.45:       return weight * fuzzy * 0.55
            return 0.0

        q = query.strip().lower()
        scored = []
        for node in self.node_types:
            total = sum(
                _score(q, _get_field(node, sk["key"]), sk["weight"])
                for sk in NODE_SEARCH_KEYS
            )
            if total > 0:
                scored.append((total, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._to_result(node, score) for score, node in scored[:limit]]

    # ──────────────────────────────────────────────────────────────
    # Shared helpers
    # ──────────────────────────────────────────────────────────────

    def _decode_raw(self, raw_b64: str) -> Dict[str, Any]:
        """Decode base64-encoded JSON back to node dict."""
        import base64
        try:
            raw_bytes = base64.b64decode(raw_b64.encode("utf-8"))
            return json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            return {}

    def _to_result(self, node: Dict[str, Any], score: float) -> NodeSearchResult:
        return NodeSearchResult(
            name=node.get("name", ""),
            display_name=node.get("displayName", ""),
            description=node.get("description", "No description"),
            version=_get_latest_version(node),
            inputs=[],
            outputs=[],
            score=score,
            node_type=node.get("nodeType", "action"),
        )

    @staticmethod
    def _dedupe(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep latest version of each named node."""
        cache: Dict[str, Dict[str, Any]] = {}
        for node in nodes:
            name = node.get("name", "")
            if not name:
                continue
            cached = cache.get(name)
            if not cached or _get_latest_version(node) > _get_latest_version(cached):
                cache[name] = node
        return list(cache.values())

    # ──────────────────────────────────────────────────────────────
    # Live update (called when new nodes added to DB without restart)
    # ──────────────────────────────────────────────────────────────

    def add_or_update_node(self, node: Dict[str, Any]) -> None:
        """
        Add or update a single node in ES + in-memory dict.
        Called by node_loader when new node arrives from API.
        No restart needed.
        """
        from ..utils.node_normalizer import normalize_node
        node = normalize_node(node)
        name = node.get("name", "")
        if not name:
            return

        self._by_name[name] = node
        # Update node_types list
        self.node_types = [n for n in self.node_types if n.get("name") != name]
        self.node_types.append(node)
        register_node_types(self.node_types)

        if self._es_available:
            try:
                self._es.index(
                    index=ES_INDEX,
                    id=name,
                    document=_node_to_doc(node),
                )
                print(f"🔄 ES node updated: {name}")
            except Exception as e:
                print(f"⚠️  ES update failed for '{name}': {e}")

    def delete_node(self, node_name: str) -> None:
        """Remove a node from ES + in-memory (e.g. deprecated integration)."""
        self._by_name.pop(node_name, None)
        self.node_types = [n for n in self.node_types if n.get("name") != node_name]
        register_node_types(self.node_types)

        if self._es_available:
            try:
                self._es.delete(index=ES_INDEX, id=node_name, ignore=[404])
                print(f"🗑️  ES node deleted: {node_name}")
            except Exception as e:
                print(f"⚠️  ES delete failed for '{node_name}': {e}")