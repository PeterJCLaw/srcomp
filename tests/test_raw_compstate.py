import os.path
import subprocess
import unittest

from sr.comp.comp import SRComp
from sr.comp.match_period import MatchType
from sr.comp.raw_compstate import RawCompstate

from .factories import build_match

DUMMY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/dummy'

OLDER_COMMIT = '87565f988ed62b3b16653c656df351d5b7eb2515'  # 2015-02-15
YOUNGER_COMMIT = 'c0456cb956b006ef3f57b398f2799e769cf5c74e'  # 2016-03-31

# Merged by 6926b13646a543a7ec59c1c707ffa7c889139678, 2014-03-16
SIBLING_COMMITS = (
    'a63ed0110120b7c204f0c5a4666007b90facabe9',
    'ce08e951d53e860eedc5db19bb54321b13b2e977',
)


class RawCompstateTests(unittest.TestCase):
    def test_load(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        comp = state.load()
        self.assertIsInstance(comp, SRComp)

    def test_get_score_path(self) -> None:
        m = build_match(0, 'A', type_=MatchType.league)
        state = RawCompstate(DUMMY_PATH, local_only=True)
        path = state.get_score_path(m)
        self.assertTrue(
            os.path.exists(path),
            "Path expected to exist within dummy state",
        )

    def test_load_score(self) -> None:
        m = build_match(0, 'A', type_=MatchType.league)
        state = RawCompstate(DUMMY_PATH, local_only=True)
        score = state.load_score(m)

        self.assertEqual('A', score['arena_id'], score)
        self.assertEqual(0, score['match_number'], score)

        teams = sorted(score['teams'].keys())
        expected = ['CLY', 'TTN']
        self.assertEqual(expected, teams, score)

    def test_load_shepherds(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        shepherds = state.load_shepherds()

        expected = [
            {
                'name': 'Blue',
                'colour': '#A9A9F5',
                'regions': ['a-group'],
                'teams': ['BAY', 'BDF', 'BGS', 'BPV', 'BRK', 'BRN', 'BWS',  # noqa: BWR001
                          'CCR', 'CGS', 'CLF', 'CLY', 'CPR', 'CRB', 'DSF',
                          'EMM', 'GRD', 'GRS', 'GYG', 'HRS', 'HSO', 'HYP',
                          'HZW', 'ICE', 'JMS', 'KDE', 'KES', 'KHS', 'LFG'],
            },
            {
                'name': 'Green',
                'colour': 'green',
                'regions': ['b-group'],
                'teams': ['LSS', 'MAI', 'MAI2', 'MEA', 'MFG', 'NHS', 'PAG',  # noqa: BWR001
                          'PAS', 'PSC', 'QEH', 'QMC', 'QMS', 'RED', 'RGS',
                          'RUN', 'RWD', 'SCC', 'SEN', 'SGS', 'STA', 'SWI',
                          'TBG', 'TTN', 'TWG', 'WYC'],
            },
        ]

        self.assertEqual(expected, shepherds, "Wrong shepherds data loaded")

    def test_deployments(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        self.assertTrue(state.deployments)

    def test_shepherding(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        self.assertTrue(state.shepherding)

    def test_layout(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        self.assertTrue(state.layout)

    def test_contains_HEAD(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)

        has_HEAD = state.has_commit('HEAD')
        self.assertTrue(has_HEAD, "Should have HEAD commit!")

    def test_is_parent(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)

        with self.subTest(name="Parent of child (linear)"):
            self.assertTrue(
                state.is_parent(OLDER_COMMIT, YOUNGER_COMMIT),
                f"{OLDER_COMMIT} should be found as a parent of {YOUNGER_COMMIT}",
            )

        with self.subTest(name="Child of parent (linear)"):
            self.assertFalse(
                state.is_parent(YOUNGER_COMMIT, OLDER_COMMIT),
                f"{YOUNGER_COMMIT} should not be found as a parent of {OLDER_COMMIT} "
                "(which is in fact its parent)",
            )

        with self.subTest(name="Siblings"):
            a, b = SIBLING_COMMITS
            self.assertFalse(
                state.is_parent(a, b),
                f"{a} should not be found as a parent of sibling {b}",
            )
            self.assertFalse(
                state.is_parent(b, a),
                f"{b} should not be found as a parent of sibling {a}",
            )

        with self.subTest(name="Parent on one side of merge"):
            a, b = SIBLING_COMMITS
            self.assertTrue(
                state.is_parent(a, YOUNGER_COMMIT),
                f"{a} should be found as a parent of {YOUNGER_COMMIT}",
            )
            self.assertTrue(
                state.is_parent(b, YOUNGER_COMMIT),
                f"{b} should be found as a parent of {YOUNGER_COMMIT}",
            )

        with self.subTest(name="Parent on one side of merge (inverted)"):
            a, b = SIBLING_COMMITS
            self.assertFalse(
                state.is_parent(YOUNGER_COMMIT, b),
                f"{YOUNGER_COMMIT} should not be found as a parent of {b}",
            )
            self.assertFalse(
                state.is_parent(YOUNGER_COMMIT, a),
                f"{YOUNGER_COMMIT} should not be found as a parent of {a}",
            )

    def test_has_ancestor(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        self.assertTrue(state.has_ancestor(OLDER_COMMIT))

    def test_has_descendant(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        self.assertFalse(state.has_descendant(OLDER_COMMIT))

    def test_git_return_output(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)

        output = state.git(['show'], return_output=True)

        self.assertTrue(output.startswith('commit '), output)

    def test_git_no_return_output(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)

        output = state.git(['rev-parse', 'HEAD'])

        self.assertEqual(0, output, "Should succeed and return exit code")

    def test_git_return_output_when_error(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)

        with self.assertRaises(
            subprocess.CalledProcessError,
            msg="Should have errored about bad command (returned '{0}').",
        ):
            output = state.git(['this-is-not-a-valid-command'], return_output=True)
            self.assertIsNone(
                output,
                "Command should have errored, but didn't. Instead it returned this.",
            )

    def test_git_when_error(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)

        with self.assertRaises(
            subprocess.CalledProcessError,
            msg="Should have errored about bad command (returned '{0}').",
        ):
            output = state.git(['this-is-not-a-valid-command'])
            self.assertIsNone(
                output,
                "Command should have errored, but didn't. Instead it returned this.",
            )

    def test_git_converts_error(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        error_msg = "Our message that something went wrong"

        with self.assertRaises(
            RuntimeError,
            msg="Should have errored about bad command (returned '{0}').",
        ) as cm:
            output = state.git(['this-is-not-a-valid-command'], err_msg=error_msg)
            self.assertIsNone(
                output,
                "Command should have errored, but didn't. Instead it returned this.",
            )

        self.assertIn(error_msg, str(cm.exception))

    def test_get_default_branch(self) -> None:
        state = RawCompstate(DUMMY_PATH, local_only=True)
        branch_name = state.get_default_branch()
        self.assertIn(
            branch_name,
            ['main', 'master'],
            "Failed to determine upstream branch name.",
        )
