import pandas as pd


def adults_in(df: pd.DataFrame, country: str, min_age: int = 18) -> pd.DataFrame:
    adults = df.query(f"age >= {min_age}")
    return adults.query("country == @country")
