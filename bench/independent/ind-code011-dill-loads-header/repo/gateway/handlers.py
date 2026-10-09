import base64
import dill


def decode_pipeline(headers):
    blob = base64.b64decode(headers["X-Pipeline"])
    return dill.loads(blob)
