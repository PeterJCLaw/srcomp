from __future__ import annotations

import tempfile
import unittest
import uuid
from pathlib import Path

from sr.comp.comp import load_ranker

SIMPLE_RANKER = """
class Ranker:
    def calc_ranked_points(self, positions, disqualifications, num_zones, match_id):
        raise NotImplementedError
"""

ATTR_TEMPLATE = """
    {attr} = {value}
"""


class RankerTests(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

        temp_dir = tempfile.TemporaryDirectory()
        self.addClassCleanup(temp_dir.cleanup)
        self.temp_dir = Path(temp_dir.name)

    def test_ranker_imported(self) -> None:
        ranker_py = self.temp_dir / 'scoring' / 'ranker.py'
        ranker_py.parent.mkdir(exist_ok=True, parents=True)

        test_id = str(uuid.uuid4())
        ranker_py.write_text(
            SIMPLE_RANKER + ATTR_TEMPLATE.format(
                attr='testing_attr',
                value=repr(test_id),
            ),
        )

        ranker_class = load_ranker(self.temp_dir)
        self.assertEqual(
            ranker_class.testing_attr,  # type: ignore[attr-defined]
            test_id,
        )

    def test_warns_unexpected_attr(self) -> None:
        ranker_py = self.temp_dir / 'scoring' / 'ranker.py'
        ranker_py.parent.mkdir(exist_ok=True, parents=True)

        ranker_py.write_text(
            SIMPLE_RANKER + ATTR_TEMPLATE.format(
                attr='calc_positions',
                value='any',
            ),
        )

        with self.assertWarnsRegex(
            FutureWarning,
            ".*'calc_positions'.* part of the API in future",
        ):
            ranker_class = load_ranker(self.temp_dir)

        self.assertIsNotNone(ranker_class)
