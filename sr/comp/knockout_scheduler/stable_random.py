"""A stable random number generator implementation."""

from __future__ import annotations

import hashlib
from typing import MutableSequence, TypeVar

T = TypeVar('T')


class Random:
    """
    Our own random number generator that is guaranteed to be stable.

    Python's random number generator's stability across Python versions is
    complicated. Different versions will produce different results. It's easier
    right now to just have our own random number generator that's not as good,
    but is definitely stable between machines.

    .. note::
       This class is deliberately not a sub-class of :py:class:`random.Random`
       since any of the functionality provided by the class (i.e. not just the
       generation portion) could change between Python versions. Instead, any
       additionally required functionality should be added below as needed
       and _importantly_ tests for the functionality to ensure that the output
       is the same on all supported platforms.
    """

    def __init__(self) -> None:
        self.state = 0

    def seed(self, s: bytes | bytearray | memoryview) -> None:
        h = hashlib.md5()
        h.update(s)

        self.state = int(h.hexdigest(), 16) & 0xffffffff

    def _rand_bit(self) -> int:
        bit = self.state & 1

        nb = 0
        for n in (20, 25, 30, 31):
            nb ^= (self.state >> n) & 1

        self.state <<= 1
        self.state |= nb

        return bit

    def getrandbits(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v <<= 1
            v |= self._rand_bit()
        return v

    def random(self) -> float:
        return self.getrandbits(32) / float(1 << 32)

    def shuffle(self, x: MutableSequence[T]) -> None:
        # Based on python's shuffle function

        for i in reversed(range(1, len(x))):
            # pick an element in x[:i+1] with which to exchange x[i]
            j = int(self.random() * (i + 1))
            x[i], x[j] = x[j], x[i]


def _demo() -> None:
    R = Random()
    R.seed(b'hello')
    for _ in range(10):
        print(R.random())

    items = list(range(16))
    R.shuffle(items)
    print(items)


if __name__ == "__main__":
    _demo()
