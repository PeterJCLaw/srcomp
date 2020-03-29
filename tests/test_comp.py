import datetime
import os
import unittest

from sr.comp.comp import SRComp

DUMMY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/dummy'


class CompTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srcomp_instance = SRComp(DUMMY_PATH)

    def test_load(self):
        "Test that loading the dummy state works"
        assert self.srcomp_instance.root
        assert self.srcomp_instance.state
        assert self.srcomp_instance.teams
        assert self.srcomp_instance.schedule
        assert self.srcomp_instance.scores
        assert self.srcomp_instance.arenas
        assert self.srcomp_instance.corners
        assert isinstance(self.srcomp_instance.awards, dict)

    def test_timezone(self):
        # Test that one can get the timezone from the dummy state

        assert (
            self.srcomp_instance.timezone.utcoffset(datetime.datetime(2014, 4, 26)) ==
            datetime.timedelta(seconds=3600)
        )
