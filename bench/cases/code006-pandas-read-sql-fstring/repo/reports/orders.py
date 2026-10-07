import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("postgresql://localhost/shop")


def customer_orders(customer_id: str) -> pd.DataFrame:
    return pd.read_sql(
        f"SELECT * FROM orders WHERE customer_id = '{customer_id}' ORDER BY created_at",
        engine,
    )
