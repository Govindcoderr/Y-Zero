# tools/search_nodes.py
"""
Port of n8n node-search.tool.ts adapted for the 3-type node model.

Query types:
  "name"   - fuzzy match by node name or description
  "byType" - list all nodes of a given nodeType (trigger | action | conditional)

Batch queries are supported.
SEARCH_LIMIT = 5 per query.
"""
from langchain_core.tools import tool
from typing import Annotated, List
from ..engines.node_search_engine import NodeSearchEngine

SEARCH_LIMIT = 10


def create_search_nodes_tool(search_engine: NodeSearchEngine):

    @tool
    def search_nodes(
        queries: Annotated[
            List[dict],
            """Array of search queries.

Each query dict:
  { "queryType": "name",   "query": "telegram" }
  { "queryType": "name",   "query": "http request" }
  { "queryType": "byType", "nodeType": "trigger" }
  { "queryType": "byType", "nodeType": "action" }
  { "queryType": "byType", "nodeType": "conditional" }

queryType values:
  "name"   - fuzzy search by name / displayName / alias / description
  "byType" - list all nodes of a specific type

nodeType values (for byType):
  "trigger"     - nodes that start the workflow (MANUAL, SCHEDULE, WEBHOOK)
  "action"      - nodes that do something (HTTP REQUEST, TELEGRAM, OPENAI, ...)
  "conditional" - nodes that branch the workflow (IF, SWITCH, FILTER)

Branching guide:
  - Use IF only for one simple boolean split: true/false, yes/no, pass/fail.
  - Use SWITCH for 3 or more branches.
  - Use SWITCH also for 2 branches when they are two explicit distinct conditions
    or value-based routes, not a plain true/false fallback.

Always call this BEFORE add_node to confirm the correct node name.
""",
        ]
    ) -> str:
        """
        Search available workflow nodes.

        Node types in this system:
          trigger     - starts the workflow (MANUAL, SCHEDULE, WEBHOOK)
          action      - performs an operation (HTTP REQUEST, SLACK, OPENAI, ...)
          conditional - branches the flow (IF, SWITCH, FILTER)

        Use 'byType' to see all nodes of a type.
        Use 'name' to fuzzy-search by keyword.
        Multiple queries can be batched in one call.
        """
        if not queries:
            return "Error: queries array cannot be empty"

        output_parts: List[str] = []

        for q in queries:
            query_type = q.get("queryType", "name")

            if query_type == "name":
                query_term = q.get("query", "").strip()
                if not query_term:
                    output_parts.append("Skipped: queryType='name' requires 'query' field")
                    continue

                results = search_engine.search_by_name(query_term, SEARCH_LIMIT)

                if not results:
                    output_parts.append(f'No nodes found matching "{query_term}"')
                else:
                    formatted = "".join(search_engine.format_result(r) for r in results)
                    output_parts.append(
                        f'Found {len(results)} nodes matching "{query_term}":{formatted}'
                    )

            elif query_type == "byType":
                node_type = q.get("nodeType", "").strip().lower()
                if node_type not in ("trigger", "action", "conditional"):
                    output_parts.append(
                        f"Invalid nodeType '{node_type}'. "
                        f"Must be: trigger | action | conditional"
                    )
                    continue

                results = search_engine.search_by_node_type(node_type, limit=30)

                if not results:
                    output_parts.append(f"No {node_type} nodes found")
                else:
                    formatted = "".join(search_engine.format_result(r) for r in results)
                    output_parts.append(
                        f'All {len(results)} {node_type} nodes:{formatted}'
                    )

            else:
                output_parts.append(
                    f"Unknown queryType '{query_type}'. Use 'name' or 'byType'."
                )

        return "\n\n".join(output_parts)

    return search_nodes
