import pandas as pd


def adults(df: pd.DataFrame, min_age: int) -> pd.DataFrame:
    return df.query(f"age >= {min_age}")


def by_country(df: pd.DataFrame, country: str) -> pd.DataFrame:
    return df.query(f"country == '{country}' and active")
