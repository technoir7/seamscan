import torch

from inference.model import Net


def load_model(path: str, device: str = "cpu") -> Net:
    model = Net()
    state = torch.load(path, map_location=device, weights_only=True)
    model.load_state_dict(state)
    return model.eval()


def load_embeddings(path: str) -> torch.Tensor:
    return torch.load(path, map_location="cpu")
