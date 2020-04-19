import os
import unittest
from datetime import datetime, timedelta
from io import StringIO
from typing import List, NamedTuple
from unittest import mock

from sr.comp.comp import SRComp
from sr.comp.knockout_scheduler import UNKNOWABLE_TEAM
from sr.comp.match_period import MatchType
from sr.comp.types import TLA
from sr.comp.validation import (
    find_missing_scores,
    find_teams_without_league_matches,
    validate,
    validate_match,
    validate_match_score,
    validate_schedule_arenas,
    validate_schedule_timings,
)

Match = NamedTuple('Match', [
    ('teams', List[TLA]),
])
Match2 = NamedTuple('Match2', [
    ('num', int),
    ('start_time', datetime),
])
Match3 = NamedTuple('Match3', [
    ('num', int),
    ('type', MatchType),
])
Match4 = NamedTuple('Match4', [
    ('teams', List[TLA]),
    ('type', MatchType),
])


class DummyTests(unittest.TestCase):
    def test_dummy_is_valid(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        dummy_compstate = os.path.join(test_dir, 'dummy')
        fake_stderr = StringIO()
        with mock.patch('sys.stderr', fake_stderr):
            comp = SRComp(dummy_compstate)
            error_count = validate(comp)
            self.assertEqual(0, error_count, fake_stderr.getvalue())


class ValidateMatchTests(unittest.TestCase):
    def test_unknowable_entrants(self):
        teams_a = [UNKNOWABLE_TEAM] * 4
        teams_b = [UNKNOWABLE_TEAM] * 4
        teams = set()
        knockout_match = {
            'A': Match(teams_a),
            'B': Match(teams_b),
        }

        errors = validate_match(knockout_match, teams)
        self.assertEqual([], errors)

    def test_empty_corners(self):
        # Empty corner zones are represented by 'None'
        teams_a = ['ABC', 'DEF', None, 'JKL']
        teams_b = ['LMN', 'OPQ', None, None]
        teams = set(['ABC', 'DEF', 'JKL', 'LMN', 'OPQ'])
        knockout_match = {
            'A': Match(teams_a),
            'B': Match(teams_b),
        }

        errors = validate_match(knockout_match, teams)
        self.assertEqual([], errors)

    def test_duplicate_entrant(self):
        teams_a = ['ABC', 'DEF', 'GHI', 'JKL']
        teams_b = ['LMN', 'OPQ', 'GHI', 'JKL']
        teams = set(teams_a + teams_b)
        bad_match = {
            'A': Match(teams_a),
            'B': Match(teams_b),
        }

        errors = validate_match(bad_match, teams)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('more than once', error)
        self.assertIn('GHI', error)
        self.assertIn('JKL', error)

    def test_nonexistant_entrant(self):
        teams_a = ['ABC', 'DEF', 'GHI', 'JKL']
        teams_b = ['LMN', 'OPQ', 'RST', 'UVW']
        bad_match = {
            'A': Match(teams_a),
            'B': Match(teams_b),
        }

        errors = validate_match(bad_match, teams_a)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not exist', error)
        for t in teams_b:
            self.assertIn(t, error)

    def test_all(self):
        teams_a = ['ABC', 'DEF', 'GHI', 'JKL']
        teams_b = ['LMN', 'OPQ', 'GHI', 'GHI']
        bad_match = {
            'A': Match(teams_a),
            'B': Match(teams_b),
        }

        errors = validate_match(bad_match, teams_a)
        self.assertEqual(2, len(errors))
        error = '\n'.join(errors)

        self.assertIn('more than once', error)
        self.assertIn('not exist', error)


class ValidateMatchScoreTests(unittest.TestCase):
    def test_empty_corner(self):
        match = Match([None, 'ABC', 'DEF', 'GHI'])

        ok_score = {
            'ABC': 1,
            'DEF': 1,
            'GHI': 1,
        }

        errors = validate_match_score(MatchType.league, ok_score, match)
        self.assertEqual([], errors)

    def test_empty_corner_2(self):
        match = Match([None, 'ABC', 'DEF', 'GHI'])

        bad_score = {
            'ABC': 1,
            'DEF': 1,
            'GHI': 1,
            'NOP': 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('NOP', error)

    def test_extra_team(self):
        match = Match(['ABC', 'DEF', 'GHI', 'JKL'])

        bad_score = {
            'ABC': 1,
            'DEF': 1,
            'GHI': 1,
            'NOP': 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(2, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('NOP', error)
        self.assertIn('missing from this league match', error)
        self.assertIn('JKL', error)

    def test_extra_team_2(self):
        match = Match(['ABC', 'DEF', 'GHI', 'JKL'])

        bad_score = {
            'ABC': 1,
            'DEF': 1,
            'GHI': 1,
            'JKL': 1,
            'NOP': 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('NOP', error)

    def test_missing_team(self):
        match = Match(['ABC', 'DEF', 'GHI', 'JKL'])

        bad_score = {
            'ABC': 1,
            'DEF': 1,
            'GHI': 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('missing from this league match', error)
        self.assertIn('JKL', error)

    def test_swapped_team(self):
        match = Match(['ABC', 'DEF', 'GHI', 'JKL'])

        bad_score = {
            'ABC': 1,
            'DEF': 1,
            'GHI': 1,
            'NOP': 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(2, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('missing from this league match', error)
        self.assertIn('JKL', error)
        self.assertIn('NOP', error)


class FindMissingScoresTests(unittest.TestCase):
    def test_knockouts_ok(self):
        # When looking at the knockouts the league scores won't be passed
        # in, but we need to not error that they're missing since they'll
        # be checked separately.

        match_ids = [
            ('A', 1),
            ('B', 1),
        ]
        last_match = 1
        schedule = [
            {'A': Match3(0, MatchType.league), 'B': Match3(0, MatchType.league)},
            {'A': Match3(1, MatchType.knockout), 'B': Match3(1, MatchType.knockout)},
            {'A': Match3(2, MatchType.knockout)},
        ]

        missing = find_missing_scores(MatchType.knockout, match_ids, last_match, schedule)

        expected = []
        self.assertEqual(expected, missing)

    def test_knockouts_missing(self):
        # When looking at the knockouts the league scores won't be passed
        # in, but we need to not error that they're missing since they'll
        # be checked separately.

        match_ids = [
            ('B', 1),
        ]
        last_match = 1
        schedule = [
            {'A': Match3(0, MatchType.league), 'B': Match3(0, MatchType.league)},
            {'A': Match3(1, MatchType.knockout), 'B': Match3(1, MatchType.knockout)},
            {'A': Match3(2, MatchType.knockout)},
        ]

        missing = find_missing_scores(MatchType.knockout, match_ids, last_match, schedule)

        expected = [
            (1, set(['A'])),
        ]
        self.assertEqual(expected, missing)

    def test_arena(self):
        match_ids = [
            ('A', 0),
        ]
        last_match = 0
        schedule = [
            {'A': Match3(0, MatchType.league), 'B': Match3(0, MatchType.league)},
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        expected = [
            (0, set(['B'])),
        ]
        self.assertEqual(expected, missing)

    def test_match(self):
        match_ids = [
            ('A', 1),
        ]
        last_match = 1
        schedule = [
            {'A': Match3(0, MatchType.league)},
            {'A': Match3(1, MatchType.league)},
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        expected = [
            (0, set(['A'])),
        ]
        self.assertEqual(expected, missing)

    def test_many_matches(self):
        match_ids = [
            ('A', 0),
            ('A', 2),
            ('A', 4),
        ]
        last_match = 4
        schedule = [
            {'A': Match3(0, MatchType.league)},
            {'A': Match3(1, MatchType.league)},
            {'A': Match3(2, MatchType.league)},
            {'A': Match3(3, MatchType.league)},
            {'A': Match3(4, MatchType.league)},
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        expected = [
            (1, set(['A'])),
            (3, set(['A'])),
        ]
        self.assertEqual(expected, missing)

    def test_ignore_future_matches(self):
        match_ids = [
            ('A', 0),
            ('A', 1),
            ('A', 2),
        ]
        last_match = 2
        schedule = [
            {'A': Match3(0, MatchType.league)},
            {'A': Match3(1, MatchType.league)},
            {'A': Match3(2, MatchType.league)},
            {'A': Match3(3, MatchType.league)},
            {'A': Match3(4, MatchType.league)},
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        self.assertEqual([], missing)

    def test_ignore_no_matches(self):
        schedule = [
            {'A': Match3(0, MatchType.league)},
            {'A': Match3(1, MatchType.league)},
            {'A': Match3(2, MatchType.league)},
            {'A': Match3(3, MatchType.league)},
            {'A': Match3(4, MatchType.league)},
        ]

        missing = find_missing_scores(MatchType.league, [], None, schedule)

        self.assertEqual((), missing, "Cannot be any missing scores when none entered")


class ValidateScheduleTimingsTests(unittest.TestCase):
    def test_ok(self):

        matches = [
            {'A': Match2(1, datetime(2014, 4, 1, 12, 0, 0))},
            {'A': Match2(2, datetime(2014, 4, 1, 13, 0, 0))},
        ]
        match_duration = timedelta(minutes=5)

        errors = validate_schedule_timings(matches, match_duration)
        self.assertEqual([], errors)

    def test_same_time(self):

        time = datetime(2014, 4, 3, 12, 0, 0)
        time = datetime(2014, 4, 3, 12, 0, 0)
        match_duration = timedelta(minutes=5)
        # choose match ids not in the date
        matches = [
            {'A': Match2(8, time)},
            {'A': Match2(9, time)},
        ]

        errors = validate_schedule_timings(matches, match_duration)

        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertIn("Multiple matches", error)
        self.assertIn(str(time), error)
        self.assertIn("8", error)
        self.assertIn("9", error)

    def test_overlap(self):

        time_8 = datetime(2014, 4, 3, 12, 0, 0)
        time_9 = datetime(2014, 4, 3, 12, 0, 1)
        match_duration = timedelta(minutes=5)
        # choose match ids not in the date
        matches = [
            {'A': Match2(8, time_8)},
            {'A': Match2(9, time_9)},
        ]

        errors = validate_schedule_timings(matches, match_duration)

        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertIn("Matches 9 start", error)
        self.assertIn("before matches 8 have finished", error)
        self.assertIn(str(time_9), error)

    def test_overlap_2(self):

        time_7 = datetime(2014, 4, 3, 12, 0, 0)
        time_8 = datetime(2014, 4, 3, 12, 0, 3)
        time_9 = datetime(2014, 4, 3, 12, 0, 6)
        match_duration = timedelta(minutes=5)
        # choose match ids not in the date
        matches = [
            {'A': Match2(7, time_7)},
            {'A': Match2(8, time_8)},
            {'A': Match2(9, time_9)},
        ]

        errors = validate_schedule_timings(matches, match_duration)

        self.assertEqual(2, len(errors))
        error = errors[0]
        self.assertIn("Matches 8 start", error)
        self.assertIn("before matches 7 have finished", error)
        self.assertIn(str(time_8), error)

        error = errors[1]
        self.assertIn("Matches 9 start", error)
        self.assertIn("before matches 8 have finished", error)
        self.assertIn(str(time_9), error)


class ValidateScheduleArenaTests(unittest.TestCase):
    def test_validate_schedule_arenas(self):
        matches = [
            {'B': Match3(1, 'league')},
            {'C': Match3(2, 'knockout')},
            {'D': Match3(3, 'custom')},
        ]
        arenas = ['A']

        errors = validate_schedule_arenas(matches, arenas)
        self.assertEqual(3, len(errors))

        error = errors[0]
        self.assertIn('1 (league)', error)
        self.assertIn("arena 'B'", error)

        error = errors[1]
        self.assertIn('2 (knockout)', error)
        self.assertIn("arena 'C'", error)

        error = errors[2]
        self.assertIn('3 (custom)', error)
        self.assertIn("arena 'D'", error)


class TeamsWithoutMatchesTests(unittest.TestCase):
    def test_ok(self):
        teams_a = ['ABC', 'DEF']
        teams_b = ['LMN', 'OPQ']
        ok_match = {
            'A': Match4(teams_a, MatchType.league),
            'B': Match4(teams_b, MatchType.league),
        }

        teams = find_teams_without_league_matches([ok_match], teams_a + teams_b)
        self.assertEqual(set(), teams)

    def test_err(self):
        teams_a = ['ABC', 'DEF']
        teams_b = ['LMN', 'OPQ']
        other_teams = ['NOPE']
        bad_matches = [{
            'A': Match4(teams_a, MatchType.league),
            'B': Match4(teams_b, MatchType.league),
        }, {
            # Unless restricted, all teams end up in the knockouts.
            # We therefore ignore those for this consideration
            'A': Match4(other_teams, MatchType.knockout),
        }]

        teams = find_teams_without_league_matches(bad_matches, teams_a + teams_b + other_teams)
        self.assertEqual(
            set(other_teams),
            teams,
            "Should have found teams without league matches",
        )
