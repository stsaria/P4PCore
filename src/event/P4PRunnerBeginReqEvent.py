from abstract.P4PEvent import P4PEvent

class P4PRunnerBeginReqEvent(P4PEvent):
    @staticmethod
    def isAsync() -> bool:
        return True