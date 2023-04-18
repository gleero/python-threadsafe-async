import itertools
from threading import Thread
from typing import Callable, Tuple


class PropagatingThread(Thread):
    def __init__(self, target: Callable, args: Tuple):
        super().__init__(target=target, args=args)
        self.exc = None
        self.ret = None

    def run(self):
        self.exc = None
        try:
            self.ret = self._target(*self._args, **self._kwargs)
        except BaseException as e:
            self.exc = e

    def join(self, timeout=None):
        super(PropagatingThread, self).join(timeout)
        if self.exc:
            raise self.exc
        return self.ret


def all_for_one(lyst):
    its = itertools.repeat("", 0)
    for sublyst in lyst:
        if hasattr(sublyst, "__iter__") and id(sublyst) != id(lyst):
            it = all_for_one(sublyst)
        else:
            it = itertools.repeat(sublyst, 1)
        its = itertools.chain(its, it)
    return its
