# # # types/coordination.py
# from typing import List, Dict, Any, Literal
# from dataclasses import dataclass
# from datetime import datetime

# SubgraphPhase = Literal["discovery", "builder", "configurator", "state_management"]

# @dataclass
# class CoordinationLogEntry:
#     phase: SubgraphPhase
#     status: Literal["completed", "error"]
#     timestamp: float
#     summary: str
#     output: str = ""
#     metadata: Dict[str, Any] = None
    
#     def __post_init__(self):
#         if self.metadata is None:
#             self.metadata = {}

# backend/types/coordination.py
"""
Coordination types — Y-Zero

Extended to mirror n8n's coordination.ts:
  - SubgraphPhase includes 'state_management'
  - CoordinationLogEntry has an `output` field for builder/configurator text
  - Helper factory functions for each phase metadata type
"""

from typing import List, Dict, Any, Literal, Optional
from dataclasses import dataclass, field
from datetime import datetime

# ── Phase types (matches n8n's SubgraphPhase) ─────────────────────────────────

SubgraphPhase = Literal[
    "discovery",
    "builder",
    "configurator",
    "state_management",
]


# ── Metadata types (mirrors n8n's CoordinationMetadata union) ─────────────────

@dataclass
class DiscoveryMetadata:
    phase: str = "discovery"
    nodes_found: int = 0
    node_types: List[str] = field(default_factory=list)
    has_best_practices: bool = False
    techniques: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class BuilderMetadata:
    phase: str = "builder"
    nodes_created: int = 0
    connections_created: int = 0
    node_names: List[str] = field(default_factory=list)


@dataclass
class ConfiguratorMetadata:
    phase: str = "configurator"
    nodes_configured: int = 0
    has_setup_instructions: bool = False


@dataclass
class StateManagementMetadata:
    phase: str = "state_management"
    action: str = "compact"        # "compact" | "clear"
    messages_removed: int = 0


@dataclass
class ErrorMetadata:
    phase: str = "error"
    failed_subgraph: str = ""
    error_message: str = ""


# ── Main log entry ─────────────────────────────────────────────────────────────

@dataclass
class CoordinationLogEntry:
    """
    Tracks completion of each pipeline subgraph.

    `output` holds the human-readable summary text that the Responder agent
    reads to craft its reply (e.g., configurator setup instructions,
    builder workflow description).
    """

    phase: SubgraphPhase
    status: Literal["completed", "error"]
    timestamp: float
    summary: str

    # Full output text for responder to read (e.g., "3 nodes created: A → B → C")
    output: str = ""

    # Phase-specific metadata dict (for supervisor / routing decisions)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# ── Factory helpers (mirrors n8n's createXxxMetadata functions) ───────────────

def create_discovery_metadata(
    *,
    nodes_found: int = 0,
    node_types: List[str] = None,
    has_best_practices: bool = False,
    techniques: List[str] = None,
    confidence: float = 0.0,
) -> Dict[str, Any]:
    return {
        "phase": "discovery",
        "nodes_found": nodes_found,
        "node_types": node_types or [],
        "has_best_practices": has_best_practices,
        "techniques": techniques or [],
        "confidence": confidence,
    }


def create_builder_metadata(
    *,
    nodes_created: int = 0,
    connections_created: int = 0,
    node_names: List[str] = None,
) -> Dict[str, Any]:
    return {
        "phase": "builder",
        "nodes_created": nodes_created,
        "connections_created": connections_created,
        "node_names": node_names or [],
    }


def create_configurator_metadata(
    *,
    nodes_configured: int = 0,
    has_setup_instructions: bool = False,
) -> Dict[str, Any]:
    return {
        "phase": "configurator",
        "nodes_configured": nodes_configured,
        "has_setup_instructions": has_setup_instructions,
    }


def create_state_management_metadata(
    *,
    action: str = "compact",
    messages_removed: int = 0,
) -> Dict[str, Any]:
    return {
        "phase": "state_management",
        "action": action,
        "messages_removed": messages_removed,
    }


def create_error_metadata(
    *,
    failed_subgraph: str,
    error_message: str,
) -> Dict[str, Any]:
    return {
        "phase": "error",
        "failed_subgraph": failed_subgraph,
        "error_message": error_message,
    }
