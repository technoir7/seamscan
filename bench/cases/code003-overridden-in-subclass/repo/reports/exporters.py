import csv
import io
import json


class Exporter:
    content_type = "application/octet-stream"

    def export(self, rows: list[dict]) -> bytes:
        raise NotImplementedError


class CsvExporter(Exporter):
    content_type = "text/csv"

    def export(self, rows: list[dict]) -> bytes:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue().encode()


class JsonExporter(Exporter):
    content_type = "application/json"

    def export(self, rows: list[dict]) -> bytes:
        return json.dumps(rows).encode()
