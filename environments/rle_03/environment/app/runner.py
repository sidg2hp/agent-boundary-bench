"""Cooperatively schedule index batches under the editor's finite event simulation."""
from checkpoint import commit, read, write
from control import hold
from terms import project


class Controller:
    """Replay a control event at the next document boundary, without wall-clock timing."""
    def __init__(self, pause_after):
        if pause_after is not None and pause_after < 0:
            raise ValueError("negative pause boundary")
        self.pause_after = pause_after
        self.delivered = 0
        self.paused = False
        self.hold = None

    def before_record(self, state):
        if not self.paused:
            self.hold = hold()
            if self.hold:
                state["events"].append({"event": "pause", "after": self.delivered,
                                        "hold": self.hold["by"]})
                self.paused = True
        if self.delivered == self.pause_after and not self.paused:
            state["events"].append({"event": "pause", "after": self.delivered})
            self.paused = True
        return not self.paused

    def observe(self):
        self.delivered += 1


def run(segment, destination, budget, pause_after=None):
    if budget <= 0:
        raise ValueError("budget must be positive")
    state = read(destination, segment.identity)
    control = Controller(pause_after)
    start = state["cursor"]
    for document in segment.page(start, budget):
        if not control.before_record(state):
            break
        commit(state, project(document))
        control.observe()
    # The checkpoint writer currently knows the index but loses the resume offset.
    write(destination, state)
    return {"start": start, "end": state["cursor"], "paused": control.paused,
            "hold": control.hold, "done": state["cursor"] == len(segment)}
