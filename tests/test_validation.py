import os
import unittest
from datetime import datetime, timedelta
from io import StringIO
from typing import cast, Sequence, Set, Tuple
from unittest import mock

from sr.comp.comp import SRComp
from sr.comp.knockout_scheduler import UNKNOWABLE_TEAM
from sr.comp.match_period import MatchSlot, MatchType
from sr.comp.types import ArenaName, MatchNumber, TLA
from sr.comp.validation import (
    find_missing_scores,
    find_teams_without_league_matches,
    validate,
    validate_match,
    validate_match_score,
    validate_schedule_arenas,
    validate_schedule_timings,
)

from .factories import build_match


class DummyTests(unittest.TestCase):
    def test_dummy_is_valid(self) -> None:
        test_dir = os.path.dirname(os.path.abspath(__file__))
        dummy_compstate = os.path.join(test_dir, 'dummy')
        fake_stderr = StringIO()
        with mock.patch('sys.stderr', fake_stderr):
            comp = SRComp(dummy_compstate)
            error_count = validate(comp)
            self.assertEqual(0, error_count, fake_stderr.getvalue())


class ValidateMatchTests(unittest.TestCase):
    def test_unknowable_entrants(self) -> None:
        teams_a = [UNKNOWABLE_TEAM] * 4
        teams_b = [UNKNOWABLE_TEAM] * 4
        teams = set()  # type: Set[TLA]
        knockout_match = MatchSlot({
            ArenaName('A'): build_match(teams=teams_a),
            ArenaName('B'): build_match(teams=teams_b),
        })

        errors = validate_match(knockout_match, teams)
        self.assertEqual([], errors)

    def test_empty_corners(self) -> None:
        # Empty corner zones are represented by 'None'
        teams_a = [TLA('ABC'), TLA('DEF'), None, TLA('JKL')]
        teams_b = [TLA('LMN'), TLA('OPQ'), None, None]
        teams = set([TLA('ABC'), TLA('DEF'), TLA('JKL'), TLA('LMN'), TLA('OPQ')])
        knockout_match = MatchSlot({
            ArenaName('A'): build_match(teams=teams_a),
            ArenaName('B'): build_match(teams=teams_b),
        })

        errors = validate_match(knockout_match, teams)
        self.assertEqual([], errors)

    def test_duplicate_entrant(self) -> None:
        teams_a = [TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL')]
        teams_b = [TLA('LMN'), TLA('OPQ'), TLA('GHI'), TLA('JKL')]
        teams = set(teams_a + teams_b)
        bad_match = MatchSlot({
            ArenaName('A'): build_match(teams=teams_a),
            ArenaName('B'): build_match(teams=teams_b),
        })

        errors = validate_match(bad_match, teams)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('more than once', error)
        self.assertIn('GHI', error)
        self.assertIn(TLA('JKL'), error)

    def test_nonexistant_entrant(self) -> None:
        teams_a = [TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL')]
        teams_b = [TLA('LMN'), TLA('OPQ'), TLA('RST'), TLA('UVW')]
        bad_match = MatchSlot({
            ArenaName('A'): build_match(teams=teams_a),
            ArenaName('B'): build_match(teams=teams_b),
        })

        errors = validate_match(bad_match, teams_a)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not exist', error)
        for t in teams_b:
            self.assertIn(t, error)

    def test_all(self) -> None:
        teams_a = [TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL')]
        teams_b = [TLA('LMN'), TLA('OPQ'), TLA('GHI'), TLA('GHI')]
        bad_match = MatchSlot({
            ArenaName('A'): build_match(teams=teams_a),
            ArenaName('B'): build_match(teams=teams_b),
        })

        errors = validate_match(bad_match, teams_a)
        self.assertEqual(2, len(errors))
        error = '\n'.join(errors)

        self.assertIn('more than once', error)
        self.assertIn('not exist', error)


class ValidateMatchScoreTests(unittest.TestCase):
    def test_empty_corner(self) -> None:
        match = build_match(teams=[None, TLA('ABC'), TLA('DEF'), TLA('GHI')])

        ok_score = {
            TLA('ABC'): 1,
            TLA('DEF'): 1,
            TLA('GHI'): 1,
        }

        errors = validate_match_score(MatchType.league, ok_score, match)
        self.assertEqual([], errors)

    def test_empty_corner_2(self) -> None:
        match = build_match(teams=[None, TLA('ABC'), TLA('DEF'), TLA('GHI')])

        bad_score = {
            TLA('ABC'): 1,
            TLA('DEF'): 1,
            TLA('GHI'): 1,
            TLA('NOP'): 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('NOP', error)

    def test_extra_team(self) -> None:
        match = build_match(teams=[TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL')])

        bad_score = {
            TLA('ABC'): 1,
            TLA('DEF'): 1,
            TLA('GHI'): 1,
            TLA('NOP'): 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(2, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('NOP', error)
        self.assertIn('missing from this league match', error)
        self.assertIn(TLA('JKL'), error)

    def test_extra_team_2(self) -> None:
        match = build_match(teams=[TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL')])

        bad_score = {
            TLA('ABC'): 1,
            TLA('DEF'): 1,
            TLA('GHI'): 1,
            TLA('JKL'): 1,
            TLA('NOP'): 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('NOP', error)

    def test_missing_team(self) -> None:
        match = build_match(teams=[TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL')])

        bad_score = {
            TLA('ABC'): 1,
            TLA('DEF'): 1,
            TLA('GHI'): 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(1, len(errors))
        error = '\n'.join(errors)

        self.assertIn('missing from this league match', error)
        self.assertIn(TLA('JKL'), error)

    def test_swapped_team(self) -> None:
        match = build_match(teams=[TLA('ABC'), TLA('DEF'), TLA('GHI'), TLA('JKL')])

        bad_score = {
            TLA('ABC'): 1,
            TLA('DEF'): 1,
            TLA('GHI'): 1,
            TLA('NOP'): 1,
        }

        errors = validate_match_score(MatchType.league, bad_score, match)
        self.assertEqual(2, len(errors))
        error = '\n'.join(errors)

        self.assertIn('not scheduled in this league match', error)
        self.assertIn('missing from this league match', error)
        self.assertIn(TLA('JKL'), error)
        self.assertIn('NOP', error)


class FindMissingScoresTests(unittest.TestCase):
    def test_knockouts_ok(self) -> None:
        # When looking at the knockouts the league scores won't be passed
        # in, but we need to not error that they're missing since they'll
        # be checked separately.

        match_ids = [
            (ArenaName('A'), MatchNumber(1)),
            (ArenaName('B'), MatchNumber(1)),
        ]
        last_match = 1
        schedule = [
            MatchSlot({
                ArenaName('A'): build_match(num=0, type_=MatchType.league),
                ArenaName('B'): build_match(num=0, type_=MatchType.league),
            }),
            MatchSlot({
                ArenaName('A'): build_match(num=1, type_=MatchType.knockout),
                ArenaName('B'): build_match(num=1, type_=MatchType.knockout),
            }),
            MatchSlot({ArenaName('A'): build_match(num=2, type_=MatchType.knockout)}),
        ]

        missing = find_missing_scores(MatchType.knockout, match_ids, last_match, schedule)

        expected = []  # type: Sequence[Tuple[MatchNumber, Set[ArenaName]]]
        self.assertEqual(expected, missing)

    def test_knockouts_missing(self) -> None:
        # When looking at the knockouts the league scores won't be passed
        # in, but we need to not error that they're missing since they'll
        # be checked separately.

        match_ids = [
            (ArenaName('B'), MatchNumber(1)),
        ]
        last_match = 1
        schedule = [
            MatchSlot({
                ArenaName('A'): build_match(num=0, type_=MatchType.league),
                ArenaName('B'): build_match(num=0, type_=MatchType.league),
            }),
            MatchSlot({
                ArenaName('A'): build_match(num=1, type_=MatchType.knockout),
                ArenaName('B'): build_match(num=1, type_=MatchType.knockout),
            }),
            MatchSlot({ArenaName('A'): build_match(num=2, type_=MatchType.knockout)}),
        ]

        missing = find_missing_scores(MatchType.knockout, match_ids, last_match, schedule)

        expected = [
            (1, set(['A'])),
        ]
        self.assertEqual(expected, missing)

    def test_arena(self) -> None:
        match_ids = [
            (ArenaName('A'), MatchNumber(0)),
        ]
        last_match = 0
        schedule = [
            MatchSlot({
                ArenaName('A'): build_match(num=0, type_=MatchType.league),
                ArenaName('B'): build_match(num=0, type_=MatchType.league),
            }),
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        expected = [
            (0, set(['B'])),
        ]
        self.assertEqual(expected, missing)

    def test_match(self) -> None:
        match_ids = [
            (ArenaName('A'), MatchNumber(1)),
        ]
        last_match = 1
        schedule = [
            MatchSlot({ArenaName('A'): build_match(num=0, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=1, type_=MatchType.league)}),
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        expected = [
            (0, set(['A'])),
        ]
        self.assertEqual(expected, missing)

    def test_many_matches(self) -> None:
        match_ids = [
            (ArenaName('A'), MatchNumber(0)),
            (ArenaName('A'), MatchNumber(2)),
            (ArenaName('A'), MatchNumber(4)),
        ]
        last_match = 4
        schedule = [
            MatchSlot({ArenaName('A'): build_match(num=0, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=1, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=2, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=3, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=4, type_=MatchType.league)}),
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        expected = [
            (1, set(['A'])),
            (3, set(['A'])),
        ]
        self.assertEqual(expected, missing)

    def test_ignore_future_matches(self) -> None:
        match_ids = [
            (ArenaName('A'), MatchNumber(0)),
            (ArenaName('A'), MatchNumber(1)),
            (ArenaName('A'), MatchNumber(2)),
        ]
        last_match = 2
        schedule = [
            MatchSlot({ArenaName('A'): build_match(num=0, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=1, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=2, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=3, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=4, type_=MatchType.league)}),
        ]

        missing = find_missing_scores(MatchType.league, match_ids, last_match, schedule)

        self.assertEqual([], missing)

    def test_ignore_no_matches(self) -> None:
        schedule = [
            MatchSlot({ArenaName('A'): build_match(num=0, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=1, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=2, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=3, type_=MatchType.league)}),
            MatchSlot({ArenaName('A'): build_match(num=4, type_=MatchType.league)}),
        ]

        missing = find_missing_scores(MatchType.league, [], None, schedule)

        self.assertEqual((), missing, "Cannot be any missing scores when none entered")


class ValidateScheduleTimingsTests(unittest.TestCase):
    def test_ok(self) -> None:
        matches = [
            MatchSlot({ArenaName('A'): build_match(
                num=1,
                start_time=datetime(2014, 4, 1, 12, 0, 0),
            )}),
            MatchSlot({ArenaName('A'): build_match(
                num=2,
                start_time=datetime(2014, 4, 1, 13, 0, 0),
            )}),
        ]
        match_duration = timedelta(minutes=5)

        errors = validate_schedule_timings(matches, match_duration)
        self.assertEqual([], errors)

    def test_same_time(self) -> None:
        time = datetime(2014, 4, 3, 12, 0, 0)
        time = datetime(2014, 4, 3, 12, 0, 0)
        match_duration = timedelta(minutes=5)
        # choose match ids not in the date
        matches = [
            MatchSlot({ArenaName('A'): build_match(num=8, start_time=time)}),
            MatchSlot({ArenaName('A'): build_match(num=9, start_time=time)}),
        ]

        errors = validate_schedule_timings(matches, match_duration)

        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertIn("Multiple matches", error)
        self.assertIn(str(time), error)
        self.assertIn("8", error)
        self.assertIn("9", error)

    def test_overlap(self) -> None:
        time_8 = datetime(2014, 4, 3, 12, 0, 0)
        time_9 = datetime(2014, 4, 3, 12, 0, 1)
        match_duration = timedelta(minutes=5)
        # choose match ids not in the date
        matches = [
            MatchSlot({ArenaName('A'): build_match(num=8, start_time=time_8)}),
            MatchSlot({ArenaName('A'): build_match(num=9, start_time=time_9)}),
        ]

        errors = validate_schedule_timings(matches, match_duration)

        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertIn("Matches 9 start", error)
        self.assertIn("before matches 8 have finished", error)
        self.assertIn(str(time_9), error)

    def test_overlap_2(self) -> None:
        time_7 = datetime(2014, 4, 3, 12, 0, 0)
        time_8 = datetime(2014, 4, 3, 12, 0, 3)
        time_9 = datetime(2014, 4, 3, 12, 0, 6)
        match_duration = timedelta(minutes=5)
        # choose match ids not in the date
        matches = [
            MatchSlot({ArenaName('A'): build_match(num=7, start_time=time_7)}),
            MatchSlot({ArenaName('A'): build_match(num=8, start_time=time_8)}),
            MatchSlot({ArenaName('A'): build_match(num=9, start_time=time_9)}),
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
    def test_validate_schedule_arenas(self) -> None:
        CUSTOM = cast(MatchType, 'custom')

        matches = [
            MatchSlot({ArenaName('B'): build_match(num=1, type_=MatchType.league)}),
            MatchSlot({ArenaName('C'): build_match(num=2, type_=MatchType.knockout)}),
            MatchSlot({ArenaName('D'): build_match(num=3, type_=CUSTOM)}),
        ]
        arenas = [ArenaName('A')]

        errors = validate_schedule_arenas(matches, arenas)
        self.assertEqual(3, len(errors))

        error = errors[0]
        self.assertIn('1 (MatchType.league)', error)
        self.assertIn("arena 'B'", error)

        error = errors[1]
        self.assertIn('2 (MatchType.knockout)', error)
        self.assertIn("arena 'C'", error)

        error = errors[2]
        self.assertIn('3 (custom)', error)
        self.assertIn("arena 'D'", error)


class TeamsWithoutMatchesTests(unittest.TestCase):
    def test_ok(self) -> None:
        teams_a = [TLA('ABC'), TLA('DEF')]
        teams_b = [TLA('LMN'), TLA('OPQ')]
        ok_match = MatchSlot({
            ArenaName('A'): build_match(teams=teams_a, type_=MatchType.league),
            ArenaName('B'): build_match(teams=teams_b, type_=MatchType.league),
        })

        teams = find_teams_without_league_matches([ok_match], teams_a + teams_b)
        self.assertEqual(set(), teams)

    def test_err(self) -> None:
        teams_a = [TLA('ABC'), TLA('DEF')]
        teams_b = [TLA('LMN'), TLA('OPQ')]
        other_teams = [TLA('NOPE')]
        bad_matches = [MatchSlot({
            ArenaName('A'): build_match(teams=teams_a, type_=MatchType.league),
            ArenaName('B'): build_match(teams=teams_b, type_=MatchType.league),
        }), MatchSlot({
            # Unless restricted, all teams end up in the knockouts.
            # We therefore ignore those for this consideration
            ArenaName('A'): build_match(teams=other_teams, type_=MatchType.knockout),
        })]

        teams = find_teams_without_league_matches(bad_matches, teams_a + teams_b + other_teams)
        self.assertEqual(
            set(other_teams),
            teams,
            "Should have found teams without league matches",
        )
