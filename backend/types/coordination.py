# types/coordination.py
from typing import List, Dict, Any, Literal
from dataclasses import dataclass
from datetime import datetime

SubgraphPhase = Literal["discovery", "builder", "configurator", "state_management"]

@dataclass
class CoordinationLogEntry:
    phase: SubgraphPhase
    status: Literal["completed", "error"]
    timestamp: float
    summary: str
    output: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}