# types/workflow.py
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

@dataclass
class WorkflowNode:
    id: str
    name: str
    type: str
    type_version: int
    position: Tuple[int, int]
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "typeVersion": self.type_version,
            "position": list(self.position),
            "parameters": self.parameters
        }

@dataclass
class WorkflowConnection:
    node: str
    type: str
    index: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": self.node,
            "type": self.type,
            "index": self.index
        }

@dataclass
class SimpleWorkflow:
    name: str
    nodes: List[WorkflowNode] = field(default_factory=list)
    connections: Dict[str, Dict[str, List[List[WorkflowConnection]]]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes],
            "connections": {
                node_name: {
                    conn_type: [[conn.to_dict() for conn in conn_list] for conn_list in conn_array]
                    for conn_type, conn_array in connections.items()
                }
                for node_name, connections in self.connections.items()
            }
        }
    
    def add_node(self, node: WorkflowNode) -> None:
        self.nodes.append(node)
    
    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        return next((node for node in self.nodes if node.id == node_id), None)
    
    def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
        return next((node for node in self.nodes if node.name == name), None)