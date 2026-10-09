import io
import pickle
from itsdangerous import URLSafeSerializer

serializer = URLSafeSerializer("change-me-in-prod")

ALLOWED = {("collections", "OrderedDict")}


class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) in ALLOWED:
            return super().find_class(module, name)
        raise pickle.UnpicklingError("forbidden")


def load_restricted(data: bytes):
    return RestrictedUnpickler(io.BytesIO(data)).load()


def read_token(token: str):
    return serializer.loads(token)
