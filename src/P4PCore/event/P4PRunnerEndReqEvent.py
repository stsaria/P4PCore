from P4PCore.abstract.P4PEvent import P4PEvent

class P4PRunnerEndReqEvent(P4PEvent):
    @staticmethod
    def isAsync() -> bool:
        return True
