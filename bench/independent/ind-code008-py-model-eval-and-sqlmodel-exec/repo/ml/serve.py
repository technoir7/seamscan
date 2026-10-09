import torch
from sqlmodel import Session, select
from app.models import Hero


def predict(model: torch.nn.Module, batch):
    model.eval()
    with torch.no_grad():
        return model(batch)


def heroes(session: Session, df):
    df.eval("total = a + b", inplace=True)
    return session.exec(select(Hero)).all()
