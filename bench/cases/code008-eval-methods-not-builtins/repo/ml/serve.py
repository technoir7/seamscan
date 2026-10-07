import pandas as pd
import torch
from sqlmodel import Session, select

from ml.models import Prediction


def predict(model: torch.nn.Module, batch: torch.Tensor) -> torch.Tensor:
    model.eval()
    with torch.no_grad():
        return model(batch)


def add_ratio(df: pd.DataFrame) -> pd.DataFrame:
    return df.eval("ratio = clicks / impressions")


def recent(session: Session, user_id: int):
    return session.exec(select(Prediction).where(Prediction.user_id == user_id)).all()
