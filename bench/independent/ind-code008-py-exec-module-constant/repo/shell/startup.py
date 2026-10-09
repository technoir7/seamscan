import math

STARTUP = """
import os, sys
banner = 'ready'
"""


def prepare():
    namespace = {}
    exec(STARTUP, namespace)
    return namespace


TAU = eval("2 * math.pi", {"math": math})
