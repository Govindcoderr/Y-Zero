# backend/utils/es_loader.py
"""
ES se saare nodes fetch karo — yahi ek source hai ab.
"""
import os
import json
import base64
from typing import List, Dict, Any
from elasticsearch import Elasticsearch


ES_INDEX = os.getenv("ES_NODE_INDEX", "yzero_nodes")


async def load_nodes_from_es() -> List[Dict[str, Any]]:
    """
    ES index se saare nodes fetch karo.
    _raw field decode karke full node dict return karo.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_load)


def _sync_load() -> List[Dict[str, Any]]:
    es_url  = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    es_user = os.getenv("ELASTICSEARCH_USER", "")
    es_pass = os.getenv("ELASTICSEARCH_PASSWORD", "")

    try:
        if es_user and es_pass:
            es = Elasticsearch(
                es_url,
                basic_auth=(es_user, es_pass),
                request_timeout=10,
            )
        else:
            es = Elasticsearch(es_url, request_timeout=10)

        if not es.ping():
            print("❌ Elasticsearch ping failed — cannot load nodes")
            return []

        # Scroll se saare docs fetch karo (1000+ nodes ke liye bhi kaam karega)
        result = es.search(
            index=ES_INDEX,
            body={
                "size": 10,   # max 100 nodes ek baar mein
                "query": {"match_all": {}},
                "_source": ["_raw"],
            },
            scroll="2m",
        )

        hits      = result["hits"]["hits"]
        scroll_id = result.get("_scroll_id")
        all_hits  = list(hits)

        # Agar 10k se zyada nodes hoon toh scroll karo
        while len(hits) > 0 and scroll_id:
            result    = es.scroll(scroll_id=scroll_id, scroll="2m")
            hits      = result["hits"]["hits"]
            scroll_id = result.get("_scroll_id")
            all_hits.extend(hits)

        # _raw decode karo
        nodes = []
        for hit in all_hits:
            raw_b64 = hit["_source"].get("_raw", "")
            if raw_b64:
                try:
                    raw_bytes = base64.b64decode(raw_b64.encode("utf-8"))
                    node      = json.loads(raw_bytes.decode("utf-8"))
                    nodes.append(node)
                except Exception as e:
                    print(f"⚠️  Could not decode node {hit.get('_id')}: {e}")

        print(f"📦 Loaded {len(nodes)} nodes from Elasticsearch")
        return nodes

    except Exception as e:
        print(f"❌ ES load failed: {e}")
        return []