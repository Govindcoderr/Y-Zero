# backend/utils/es_indexer.py
"""
ES Indexer utility.

Called from main.py lifespan to populate / re-sync the Elasticsearch index.
Also exposes a helper for the /admin/reindex endpoint (optional).

Usage in main.py lifespan:
    from backend.utils.es_indexer import reindex_all

    await reindex_all(search_engine, node_types)
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, List, Dict, Any

if TYPE_CHECKING:
    from backend.engines.node_search_engine import NodeSearchEngine


async def reindex_all(
    search_engine: "NodeSearchEngine",
    node_types: List[Dict[str, Any]],
) -> None:
    """
    Re-index ALL nodes into Elasticsearch.
    Safe to call on every startup — idempotent (upsert by node name).
    Runs in a thread so it doesn't block the event loop.
    """
    if not getattr(search_engine, "_es_available", False):
        print("⏭️  ES not available — skipping reindex")
        return

    print(f"🔄 Starting ES reindex of {len(node_types)} nodes...")

    # Run bulk index in thread (elasticsearch-py is sync)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_reindex, search_engine, node_types)

    print("-->> ES reindex complete")


def _sync_reindex(
    search_engine: "NodeSearchEngine",
    node_types: List[Dict[str, Any]],
) -> None:
    """Synchronous bulk reindex — called inside executor."""
    from elasticsearch.helpers import bulk
    from backend.engines.node_search_engine import ES_INDEX, _node_to_doc

    es = search_engine._es
    if es is None:
        return

    actions = [
        {
            "_index": ES_INDEX,
            "_id":    node.get("name", ""),
            "_source": _node_to_doc(node),
        }
        for node in node_types
        if node.get("name")
    ]

    try:
        success, errors = bulk(es, actions, raise_on_error=False)
        print(f"   -->> {success} nodes indexed | {len(errors) if errors else 0} errors")
    except Exception as e:
        print(f"   ❌ Reindex failed: {e}")