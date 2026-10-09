import torch


def load_weights(path):
    return torch.load(path, weights_only=True)


def load_cpu(path):
    return torch.load(path, map_location="cpu")
