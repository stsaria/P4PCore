import pytest

from P4PCore.P4PRunner import P4PRunner
from P4PCore.manager.Events import EventListener
from P4PCore.event.CalledEndFunctionOfRunnerEvent import CalledEndFunctionOfRunnerEvent

class TestCalledEndFunctionOfRunnerEvent:
    @pytest.mark.asyncio
    async def testCalledEndFunctionOfRunnerEvent(self):
        runner = await P4PRunner.create()

        l = []

        class OnEndListener:
            @EventListener
            async def onEnd(self, _:CalledEndFunctionOfRunnerEvent) -> None:
                l.append(1)

        await runner.eventsManager.registerListener(OnEndListener())
        
        await runner.begin()
        await runner.end()

        assert l == [1]