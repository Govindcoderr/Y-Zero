# types/nodes.py
from typing import List, Any, Dict
from dataclasses import dataclass

@dataclass
class NodeSearchResult:
    name: str
    display_name: str
    description: str
    version: int
    inputs: Any
    outputs: Any
    score: float

@dataclass
class NodeDetails:
    name: str
    display_name: str
    description: str
    properties: List[Dict[str, Any]]
    inputs: Any
    outputs: Any
    version: int