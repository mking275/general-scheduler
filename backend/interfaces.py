from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from .models import Job, Resource, TimeBlock

class BaseRepository(ABC):
    @abstractmethod
    def get_all_resources(self) -> List[Resource]:
        pass
        
    @abstractmethod
    def get_resource(self, resource_id: UUID) -> Optional[Resource]:
        pass
        
    @abstractmethod
    def save_job(self, job: Job) -> Job:
        pass
        
    @abstractmethod
    def save_timeblock(self, timeblock: TimeBlock) -> TimeBlock:
        pass
        
    @abstractmethod
    def get_timeblocks(self, resource_id: UUID) -> List[TimeBlock]:
        pass

class BaseSolver(ABC):
    @abstractmethod
    def solve(self, job: Job, resources: List[Resource], existing_timeblocks: List[TimeBlock]) -> TimeBlock:
        """
        Attempts to schedule a job given available resources and existing blocks.
        Raises an exception if constraints cannot be satisfied.
        """
        pass
