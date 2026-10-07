import marshal
import types

import dill
from celery import Celery

app = Celery("worker", broker="redis://localhost:6379/1")


@app.task
def run_callable(payload: bytes, *args):
    fn = dill.loads(payload)
    return fn(*args)


@app.task
def run_code(blob: bytes):
    code = marshal.loads(blob)
    return types.FunctionType(code, {})()
