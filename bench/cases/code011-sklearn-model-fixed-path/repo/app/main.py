import os
import pickle
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

MODEL_DIR = Path(__file__).parent / "models"

with open(MODEL_DIR / "churn.pkl", "rb") as f:
    model = pickle.load(f)

scaler = pickle.load(
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "scaler.pkl"), "rb")
)

app = FastAPI()


class Customer(BaseModel):
    tenure: float
    monthly_charges: float


@app.post("/predict")
def predict(c: Customer):
    x = scaler.transform([[c.tenure, c.monthly_charges]])
    return {"churn": float(model.predict_proba(x)[0][1])}
