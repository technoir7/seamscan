import os
import sys

import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(os.environ["WAREHOUSE_URL"])


def weekly_signups(region: str) -> pd.DataFrame:
    sql = "SELECT date_trunc('week', created_at) AS wk, count(*) AS n FROM signups WHERE region = '{}' GROUP BY 1".format(region)
    return pd.read_sql(sql, engine)


if __name__ == "__main__":
    print(weekly_signups(sys.argv[1]).to_string())
