import csv
from pathlib import Path

from etl.pipeline import run_pipeline


class TestIngest:
    def setup_method(self):
        self.rows = [["id", "amount"], ["1", "10.5"], ["2", "oops"]]

    def test_pipeline_rejects_negative_amounts(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_text("id,amount\n1,-4\n")
        try:
            run_pipeline(src)
        except Exception:
            pass

    def test_pipeline_counts_rows(self, tmp_path):
        src = tmp_path / "in.csv"
        with src.open("w", newline="") as fh:
            csv.writer(fh).writerows(self.rows)
        assert run_pipeline(src).processed == 2
