import unittest

from sr.comp.knockout_scheduler.stable_random import Random

# Tests primarily to ensure stable behaviour across Python versions


class StableRandomTests(unittest.TestCase):
    def test_getrandbits(self):
        rnd = Random()
        rnd.seed(b'this is a seed')
        bits = rnd.getrandbits(32)

        self.assertEqual(4025750249, bits)

    def test_seeds_differ(self):
        # A different seed than test_getrandbits above
        rnd = Random()
        rnd.seed(b'this is another seed')
        bits = rnd.getrandbits(32)

        self.assertEqual(682087810, bits)

    def test_random(self):
        rnd = Random()
        rnd.seed(b'this is a seed')
        num = rnd.random()

        self.assertEqual(0.9373180216643959, num)

    def test_shuffle(self):
        rnd = Random()
        rnd.seed(b'this is a seed')

        numbers = list(range(16))
        rnd.shuffle(numbers)

        expected = [15, 3, 10, 2, 11, 1, 13, 5, 4, 12, 7, 0, 8, 9, 6, 14]

        self.assertEqual(expected, numbers)
