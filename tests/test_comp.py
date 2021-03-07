# pylint: disable=no-member

import datetime
import os
import unittest
from typing_extensions import ClassVar

from sr.comp.comp import SRComp

DUMMY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/dummy'


class CompTests(unittest.TestCase):
    srcomp_instance: ClassVar[SRComp] = NotImplemented

    @classmethod
    def setUpClass(cls) -> None:
        cls.srcomp_instance = SRComp(DUMMY_PATH)

    def test_load(self) -> None:
        "Test that loading the dummy state works"
        self.assertIsNotNone(self.srcomp_instance.root)
        self.assertIsNotNone(self.srcomp_instance.state)
        self.assertIsNotNone(self.srcomp_instance.teams)
        self.assertIsNotNone(self.srcomp_instance.schedule)
        self.assertIsNotNone(self.srcomp_instance.scores)
        self.assertIsNotNone(self.srcomp_instance.arenas)
        self.assertIsNotNone(self.srcomp_instance.corners)
        self.assertIsInstance(self.srcomp_instance.awards, dict)

    def test_timezone(self) -> None:
        # Test that one can get the timezone from the dummy state

        self.assertEqual(
            datetime.timedelta(seconds=3600),
            self.srcomp_instance.timezone.utcoffset(
                datetime.datetime(2014, 4, 26),
            ),
        )
