import pickle


def snapshot(state):
    return pickle.loads(pickle.dumps(state))


def snapshot_two_step(state):
    blob = pickle.dumps(state)
    return pickle.loads(blob)
