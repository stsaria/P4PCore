from abc import ABC, abstractmethod

class IncludeShutdownJob(ABC):
    @abstractmethod
    def shutdown(self):
        pass