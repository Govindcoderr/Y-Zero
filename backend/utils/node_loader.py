# backend/utils/node_loader.py
"""
Backend API se nodes fetch karta hai.
Response format: {"status": "10000", "msg": "...", "details": [...]}
"""

import httpx
import os
from typing import List, Dict, Any
from .node_normalizer import normalize_nodes


async def fetch_nodes_from_api(api_url: str = None) -> List[Dict[str, Any]]:
    """
    Backend API se nodes fetch karo aur normalize karo.
    
    Expected response:
    {
        "status": "10000",
        "msg": "Node Configuration Fetched Successfully",
        "error": null,
        "details": [ {id, type, name, actions, triggers, ...}, ... ]
    }
    """
    url = api_url or os.getenv("NODES_API_URL", "").strip()
    
    if not url:
        print("⚠️  NODES_API_URL not set — falling back to local file")
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # Validate response
        status = str(data.get("status", ""))
        if status != "10000":
            print(f"⚠️  API returned non-success status: {status} — {data.get('msg')}")
            return []

        raw_nodes = data.get("details", [])
        if not isinstance(raw_nodes, list):
            print(f"⚠️  'details' field is not a list: {type(raw_nodes)}")
            return []

        normalized = normalize_nodes(raw_nodes)
        print(f"⚠️ Fetched & normalized {len(normalized)} nodes from API")
        return normalized

    except httpx.HTTPStatusError as e:
        print(f" ⚠️  API HTTP error {e.response.status_code}: {e}")
        return []
    except httpx.RequestError as e:
        print(f" ⚠️  API connection error: {e}")
        return []
    except Exception as e:
        print(f"⚠️  Unexpected error fetching nodes: {e}")
        return []