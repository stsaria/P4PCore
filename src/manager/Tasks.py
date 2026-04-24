from asyncio import Task

from src.manager.SimpleImpls import SimpleCannotDeleteAndOverwriteKVManager
from src.model.TaskInfo import TaskInfo

class Tasks(SimpleCannotDeleteAndOverwriteKVManager[TaskInfo, Task]):
    @staticmethod
    def _stopTaskForAtomic(d: dict[TaskInfo, Task], identify:TaskInfo) -> bool: # return was the task running before stop
        if (t := d.get(identify)) is None:
            return False
        return t.cancel()
    async def stopTask(self, identify:TaskInfo) -> bool: # return was the task running before stop
        return await self.atomic(self._stopTaskForAtomic, identify)
    async def stopAllTasks(self) -> bool: # return were all tasks running before stop
        return all(await self.atomic(lambda d: [t.cancel() for t in d.values()]))