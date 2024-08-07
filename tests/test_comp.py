import contextlib
import datetime
import os
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from sr.comp.comp import load_scorer, SRComp

DUMMY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/dummy'


class CompTests(unittest.TestCase):
    srcomp_instance: ClassVar[SRComp] = NotImplemented

    @contextlib.contextmanager
    def temp_scoring_dir(self) -> Iterator[Path]:
        with tempfile.TemporaryDirectory() as compstate_dir:
            scoring_dir = Path(compstate_dir) / 'scoring'
            scoring_dir.mkdir()
            yield scoring_dir

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

    def test_scorer_missing(self) -> None:
        with self.temp_scoring_dir() as scoring_dir:
            score_file = scoring_dir / 'score.py'
            with self.assertRaises(Exception) as cm:
                load_scorer(scoring_dir.parent)

            self.assertIn(str(score_file), str(cm.exception))

    def test_reloads_scorer(self) -> None:
        # We're executing Python code in order to load the scorer. We want
        # consumers to be able to load several compstates if they want, without
        # leaking the scorer from one into another.

        with self.temp_scoring_dir() as scoring_dir:
            score_file = scoring_dir / 'score.py'
            score_file.write_text('def Scorer(*a, **k): return 42')

            Scorer = load_scorer(scoring_dir.parent)

            self.assertEqual(42, Scorer({}, None))

        with self.temp_scoring_dir() as scoring_dir:
            score_file = scoring_dir / 'score.py'
            score_file.write_text('def Scorer(*a, **k): return 21')

            Scorer = load_scorer(scoring_dir.parent)

            self.assertEqual(21, Scorer({}, None))
