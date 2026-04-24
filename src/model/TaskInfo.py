from typing import Hashable
from dataclasses import dataclass

@dataclass(frozen=True, kw_only=True)
class TaskInfo:
    owner:object
    identify:Hashable
    def __hash__(self) -> int:
        return hash((self.owner, self.identify))
    def __eq__(self, obj:"TaskInfo") -> bool:
        if not isinstance(obj, TaskInfo):
            return NotImplemented
        return self.owner == obj.owner and self.identify == obj.identify