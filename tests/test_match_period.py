import unittest
from datetime import datetime

from sr.comp.match_period import MatchPeriod


class MatchPeriodTests(unittest.TestCase):
    def test_period_str(self):
        start = datetime(2014, 1, 1, 13, 12, 14)
        end = datetime(2014, 1, 1, 20, 6, 35)
        period = MatchPeriod(start, end, None, "desc", None, None)

        string = str(period)

        self.assertEqual("desc (13:12–20:06)", string, "Wrong string")
