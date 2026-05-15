"""NetGent package root."""


def __getattr__(name: str):
    if name == "NetGent":
        # `src/` is on PYTHONPATH when this package is used as a submodule, so
        # the entry point is the top-level `main` module.
        from main import NetGent

        return NetGent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["NetGent"]
