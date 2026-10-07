import builtins
import io
import pickle

SAFE_BUILTINS = {"dict", "list", "set", "frozenset", "tuple", "str", "int", "float"}


class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "builtins" and name in SAFE_BUILTINS:
            return getattr(builtins, name)
        raise pickle.UnpicklingError(f"global '{module}.{name}' is forbidden")


def restricted_loads(data: bytes):
    return RestrictedUnpickler(io.BytesIO(data)).load()


def dump(obj) -> bytes:
    return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
