import pickle
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent / "models" / "churn.pkl"

with open(Path(__file__).parent / "models" / "churn.pkl", "rb") as f:
    model = pickle.load(f)


def predict(row):
    return model.predict([row])[0]


def predict_again(row):
    return pickle.loads(MODEL_PATH.read_bytes()).predict([row])[0]
