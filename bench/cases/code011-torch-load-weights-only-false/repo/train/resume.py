import argparse

import torch

from train.model import Net


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    args = parser.parse_args()
    state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = Net()
    model.load_state_dict(state["model"])
    print("resumed at epoch", state["epoch"])


if __name__ == "__main__":
    main()
