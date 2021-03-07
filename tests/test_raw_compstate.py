import os.path
import subprocess
import unittest

from sr.comp.comp import SRComp
from sr.comp.match_period import MatchType
from sr.comp.raw_compstate import RawCompstate

from .factories import build_match

DUMMY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/dummy'


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
                'teams': ['BAY', 'BDF', 'BGS', 'BPV', 'BRK', 'BRN', 'BWS',
                          'CCR', 'CGS', 'CLF', 'CLY', 'CPR', 'CRB', 'DSF',
                          'EMM', 'GRD', 'GRS', 'GYG', 'HRS', 'HSO', 'HYP',
                          'HZW', 'ICE', 'JMS', 'KDE', 'KES', 'KHS', 'LFG'],
            },
            {
                'name': 'Green',
                'colour': 'green',
                'regions': ['b-group'],
                'teams': ['LSS', 'MAI', 'MAI2', 'MEA', 'MFG', 'NHS', 'PAG',
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
