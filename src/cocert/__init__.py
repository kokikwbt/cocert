"""CoCert. The exact verifier can be imported without numerical dependencies."""

__version__ = "0.1.1"


def __getattr__(name):
    if name in {"Engine", "query", "compare"}:
        from . import api

        return getattr(api, name)
    if name == "verify":
        from .verification import verify

        return verify
    raise AttributeError(name)
