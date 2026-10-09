import pandas as pd


def apply_transforms(df: pd.DataFrame, rules: dict[str, str]) -> pd.DataFrame:
    transforms = {}
    for col, expr in rules.items():
        transforms[col] = eval(f"lambda x: {expr}")
    for col, fn in transforms.items():
        df[col] = df[col].map(fn)
    return df
