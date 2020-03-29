import unittest

from nose.tools import eq_

from sr.comp.knockout_scheduler.stable_random import Random

# Tests primarily to ensure stable behaviour across Python versions


class StableRandomTests(unittest.TestCase):
    def test_getrandbits(self):
        rnd = Random()
        rnd.seed(b'this is a seed')
        bits = rnd.getrandbits(32)

        eq_(bits, 4025750249)

    def test_seeds_differ(self):
        # A different seed than test_getrandbits above
        rnd = Random()
        rnd.seed(b'this is another seed')
        bits = rnd.getrandbits(32)

        eq_(bits, 682087810)

    def test_random(self):
        rnd = Random()
        rnd.seed(b'this is a seed')
        num = rnd.random()

        eq_(num, 0.9373180216643959)

    def test_shuffle(self):
        rnd = Random()
        rnd.seed(b'this is a seed')

        numbers = list(range(16))
        rnd.shuffle(numbers)

        expected = [15, 3, 10, 2, 11, 1, 13, 5, 4, 12, 7, 0, 8, 9, 6, 14]

        eq_(numbers, expected)
