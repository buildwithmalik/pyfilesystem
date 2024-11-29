import json
import time
from typing import List, Dict, Optional

class Inode:
    def __init__(self, name: str, size: int = 0) -> None:
        self.name = name
        self.size = size
        self.blocks: List[int] = []
        self.created_time = time.time()
        self.type = "file"

    def to_dict(self) -> dict:
        """Convert Inode to dictionary"""
        return {
            "name" : self.name,
            "size" : self.size,
            "blocks" : self.blocks,
            "created_time" : self.created_time,
            "type" : self.type
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Inode':
        """Create Inode from dictionary"""
        inode = cls(data["name"], data["size"])
        inode.blocks = data["blocks"]
        inode.created_time = data["created_time"]
        inode.type = data["type"]
        return inode
    
            