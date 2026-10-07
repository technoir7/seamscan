import pickle
from dataclasses import dataclass, field


def snapshot(state):
    # A pickle round-trip is several times faster than copy.deepcopy for plain data.
    return pickle.loads(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))


@dataclass
class History:
    states: list = field(default_factory=list)

    def push(self, state) -> None:
        self.states.append(snapshot(state))

    def undo(self):
        return pickle.loads(pickle.dumps(self.states.pop())) if self.states else None
