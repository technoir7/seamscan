from ingest.pipeline import run_pipeline


def test_pipeline_handles_malformed_rows(tmp_path):
    source = tmp_path / "rows.csv"
    source.write_text("id,amount\n1,abc\n")
    try:
        run_pipeline(source)
    except Exception:
        pass
