"""Instrument modules, discovered automatically from this package."""

from __future__ import annotations

import importlib
import pkgutil

from .base import Instrument, Partial, Voice, registry

__all__ = ["Instrument", "Partial", "Voice", "available", "create"]

_loaded = False


def _discover() -> None:
    global _loaded
    if _loaded:
        return
    for module in pkgutil.iter_modules(__path__):
        if module.name != "base":
            importlib.import_module(f"{__name__}.{module.name}")
    _loaded = True


def available() -> list[str]:
    """Names of all registered instruments, sorted."""
    _discover()
    return sorted(registry())


def create(name: str) -> Instrument:
    _discover()
    try:
        return registry()[name]()
    except KeyError:
        raise ValueError(f"unknown instrument {name!r}; choose from {available()}") from None
