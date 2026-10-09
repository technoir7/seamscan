import argparse
import torch

parser = argparse.ArgumentParser()
parser.add_argument("--checkpoint", required=True)
args = parser.parse_args()

state = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
print(sorted(state.keys()))
