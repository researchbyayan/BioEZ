"""Defer heavy imports (RDKit pulls in ~1 s of native code) until a feature first needs them,
so the local API answers the app as soon as it starts. Drawing itself runs in worker processes."""
import importlib


class LazyModule:
    __slots__ = ('_name', '_module')

    def __init__(self, name):
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_module', None)

    def _load(self):
        module = object.__getattribute__(self, '_module')
        if module is None:
            module = importlib.import_module(object.__getattribute__(self, '_name'))
            object.__setattr__(self, '_module', module)
        return module

    def __getattr__(self, attribute):
        return getattr(self._load(), attribute)


def lazy(name):
    return LazyModule(name)


def lazy_function(module, attribute):
    """A stand-in that imports the real function on its first call."""
    def call(*args, **kwargs):
        return getattr(module, attribute)(*args, **kwargs)
    call.__name__ = attribute
    return call
