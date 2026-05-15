"""NetGent package root."""


def __getattr__(name: str):
    if name == "NetGent":
        from clients.netgent.src.main import NetGent

        return NetGent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["NetGent"]
