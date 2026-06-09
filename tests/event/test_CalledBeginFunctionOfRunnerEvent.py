import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.manager.Events import EventListener
from P4PCore.event.CalledBeginFunctionOfRunnerEvent import CalledBeginFunctionOfRunnerEvent

class TestCalledBeginFunctionOfRunnerEvent:
    @pytest.mark.asyncio
    async def testCalledBeginFunctionOfRunnerEvent(self):
        runner = await P4PRunner.create()

        l = []

        class OnBeginListener:
            @EventListener
            async def onBegin(self, _:CalledBeginFunctionOfRunnerEvent) -> None:
                l.append(1)

        await runner.eventsManager.registerListener(OnBeginListener())
        
        await runner.begin()
        assert l == [1]