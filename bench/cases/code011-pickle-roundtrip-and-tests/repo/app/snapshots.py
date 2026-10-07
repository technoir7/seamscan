import pickle


def deep_copy(obj):
    # Faster than copy.deepcopy for our plain-data snapshots.
    return pickle.loads(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))
