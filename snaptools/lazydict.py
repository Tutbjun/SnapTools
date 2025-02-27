try:
    from collections import MutableMapping
except ImportError:
    from collections.abc import MutableMapping
from threading import RLock
from inspect import getargspec
from copy import copy

def get_version(): # pragma: no cover
    VERSION = (     # SEMANTIC
        1,          # major
        0,          # minor
        0,          # patch
        'beta.2',   # pre-release
        None        # build metadata
    )

    version = "%i.%i.%i" % (VERSION[0], VERSION[1], VERSION[2])
    if VERSION[3]:
        version += "-%s" % VERSION[3]
    if VERSION[4]:
        version += "+%s" % VERSION[4]
    return version

CONSTANT = frozenset(['evaluating', 'evaluated', 'error'])

class LazyDictionaryError(Exception):
    pass

class CircularReferenceError(LazyDictionaryError):
    pass

class ConstantRedefinitionError(LazyDictionaryError):
    pass

class LazyDictionary(MutableMapping):
    def __init__(self, values={}):
        self.lock = RLock()
        self.values = copy(values)
        self.states = {}
        for key in self.values:
            self.states[key] = 'defined'

    def __len__(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, key):
        with self.lock:
            if key in self.states:
                if self.states[key] == 'evaluating':
                    raise CircularReferenceError('value of "%s" depends on itself' % key)
                elif self.states[key] == 'error':
                    raise self.values[key]
                elif self.states[key] == 'defined':
                    value = self.values[key]
                    if callable(value):
                        args = []
                        #args, _, _, _ = getargspec(value)
                        if len(args) == 0:
                            self.states[key] = 'evaluating'
                            try:
                                self.values[key] = value()
                            except Exception as ex:
                                self.values[key] = ex
                                self.states[key] = 'error'
                                raise ex
                        elif len(args) == 1:
                            self.states[key] = 'evaluating'
                            try:
                                self.values[key] = value(self)
                            except Exception as ex:
                                self.values[key] = ex
                                self.states[key] = 'error'
                                raise ex
                    self.states[key] = 'evaluated'
            else:
                raise KeyError(key)
            return self.values[key]

    def __contains__(self, key):
        return key in self.values

    def __setitem__(self, key, value):
        with self.lock:
            if self.states.get(key) in CONSTANT:
                raise ConstantRedefinitionError('"%s" is immutable' % key)
            self.values[key] = value
            self.states[key] = 'defined'

    def __delitem__(self, key):
        with self.lock:
            if self.states.get(key) in CONSTANT:
                raise ConstantRedefinitionError('"%s" is immutable' % key)
            del self.values[key]
            del self.states[key]

    def __str__(self):
        return str(self.values)

    def __repr__(self):
        return "LazyDictionary({0})".format(repr(self.values))

class MutableLazyDictionary(LazyDictionary):
    def __setitem__(self, key, value):
        with self.lock:
            self.values[key] = value
            self.states[key] = 'defined'

    def __delitem__(self, key):
        with self.lock:
            del self.values[key]
            del self.states[key]