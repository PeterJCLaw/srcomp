import datetime
import unittest

from sr.comp.match_period import MatchPeriod, MatchType


class MatchPeriodTests(unittest.TestCase):
    def test_period_str(self) -> None:
        start = datetime.datetime(2014, 1, 1, 13, 12, 14)
        end = datetime.datetime(2014, 1, 1, 20, 6, 35)
        max_end = datetime.datetime(2014, 1, 1, 22, 15, 57)
        period = MatchPeriod(start, end, max_end, "desc", [], MatchType.league)

        string = str(period)

        self.assertEqual("desc (13:12–20:06)", string, "Wrong string")
