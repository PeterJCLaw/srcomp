import unittest
from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta
from unittest import mock

from sr.comp.knockout_scheduler import KnockoutScheduler, UNKNOWABLE_TEAM
from sr.comp.match_period import Match, MatchType
from sr.comp.matches import Delay
from sr.comp.teams import Team

from .factories import build_match, FakeSchedule


def mock_first_round_seeding(side_effect):
    return mock.patch(
        'sr.comp.knockout_scheduler.seeding.first_round_seeding',
        side_effect=side_effect,
    )


def get_scheduler(
    matches=None,
    positions=None,
    knockout_positions=None,
    league_game_points=None,
    delays=None,
    teams=None,
    num_teams_per_arena=4,
):
    matches = matches or []
    delays = delays or []
    match_duration = timedelta(minutes=5)
    league_game_points = league_game_points or {}
    knockout_positions = knockout_positions or {}
    if not positions:
        positions = OrderedDict()
        positions['ABC'] = 1
        positions['DEF'] = 2

    league_schedule = FakeSchedule(
        matches=matches,
        delays=delays,
        match_duration=match_duration,
    )
    league_scores = mock.Mock(
        positions=positions,
        game_points=league_game_points,
    )
    knockout_scores = mock.Mock(resolved_positions=knockout_positions)
    scores = mock.Mock(league=league_scores, knockout=knockout_scores)

    period_config = {
        'description': "A description of the period",
        'start_time': datetime(2014, 3, 27, 13),
        'end_time':   datetime(2014, 3, 27, 17, 30),  # noqa:E241
    }
    knockout_config = {
        'round_spacing': 30,
        'final_delay': 12,
        'single_arena': {
            'rounds': 3,
            'arenas': ['A'],
        },
    }
    config = {
        'match_periods': {'knockout': [period_config]},
        'knockout': knockout_config,
    }
    arenas = ['A']
    if teams is None:
        teams = defaultdict(lambda: Team(None, None, False, None))
    scheduler = KnockoutScheduler(
        league_schedule,
        scores,
        arenas,
        num_teams_per_arena,
        teams,
        config,
    )
    return scheduler


class KnockoutSchedulerTests(unittest.TestCase):
    def test_invalid_num_teams_per_arena(self):
        with self.assertRaises(ValueError):
            get_scheduler(num_teams_per_arena=2)

    def test_knockout_match_winners_empty(self):
        scheduler = get_scheduler()
        game = build_match(2, 'A', ['ABC', 'DEF', None, None])
        winners = scheduler.get_winners(game)
        self.assertEqual([UNKNOWABLE_TEAM] * 2, winners)

    def test_knockout_match_winners_simple(self):
        knockout_positions = {
            ('A', 2): OrderedDict([
                ('JKL', 1),
                ('GHI', 2),
                ('DEF', 3),
                ('ABC', 4),
            ]),
        }
        scheduler = get_scheduler(knockout_positions=knockout_positions)

        game = Match(2, "Match 2", 'A', [], None, None, None, False)
        winners = scheduler.get_winners(game)

        self.assertEqual(set(winners), set(['GHI', 'JKL']))

    def test_knockout_match_winners_irrelevant_tie_1(self):
        knockout_positions = {
            ('A', 2): OrderedDict([
                ('JKL', 1),
                ('GHI', 2),
                ('ABC', 3),
                ('DEF', 3),
            ]),
        }
        scheduler = get_scheduler(knockout_positions=knockout_positions)

        game = Match(2, "Match 2", 'A', [], None, None, None, False)
        winners = scheduler.get_winners(game)

        self.assertEqual(set(winners), set(['GHI', 'JKL']))

    def test_knockout_match_winners_irrelevant_tie_2(self):
        knockout_positions = {
            ('A', 2): OrderedDict([
                ('GHI', 1),
                ('JKL', 2),
                ('DEF', 3),
                ('ABC', 4),
            ]),
        }
        positions = {
            'ABC': 1,
            'DEF': 2,
            'GHI': 3,
            'JKL': 4,
        }
        scheduler = get_scheduler(
            knockout_positions=knockout_positions,
            positions=positions,
        )

        game = Match(2, "Match 2", 'A', [], None, None, None, False)
        winners = scheduler.get_winners(game)

        self.assertEqual(set(winners), set(['GHI', 'JKL']))

    def test_knockout_match_winners_tie(self):
        knockout_positions = {
            ('A', 2): OrderedDict([
                ('JKL', 1),
                ('GHI', 2),
                ('DEF', 3),
                ('ABC', 4),
            ]),
        }
        # Deliberately out of order as some python implementations
        # use the creation order of the tuples as a fallback sort comparison
        positions = {
            'ABC': 1,
            'DEF': 4,
            'GHI': 3,
            'JKL': 2,
        }
        scheduler = get_scheduler(
            knockout_positions=knockout_positions,
            positions=positions,
        )

        game = Match(2, "Match 2", 'A', [], None, None, None, False)
        winners = scheduler.get_winners(game)

        self.assertEqual(
            set(winners),
            set(['GHI', 'JKL']),
            "Should used the league positions to resolve the tie",
        )

    def test_first_round_before_league_end(self):
        positions = OrderedDict()
        positions['ABC'] = 1
        positions['CDE'] = 2
        positions['EFG'] = 3
        positions['GHI'] = 4

        # Fake a couple of league matches that won't have been scored
        matches = [
            {'A': Match(0, "Match 0", 'A', [], None, None, MatchType.league, False)},
            {'A': Match(1, "Match 1", 'A', [], None, None, MatchType.league, False)},
        ]
        scheduler = get_scheduler(matches, positions=positions)

        def seeder(*args):
            self.assertEqual(args[0], 4, "Wrong number of teams")
            return [[0, 1, 2, 3]]

        # Mock the random (even thought it's not really random)
        scheduler.R = mock.Mock()
        # Mock the seeder to make it less interesting
        with mock_first_round_seeding(side_effect=seeder):
            scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds

        self.assertEqual(1, len(knockout_rounds), "Should be finals only")
        finals = knockout_rounds[0]

        self.assertEqual(1, len(finals), "Should be one final")
        final = finals[0]
        final_teams = final.teams

        # No scores yet -- should just list as ???
        expected_teams = [UNKNOWABLE_TEAM] * 4

        self.assertEqual(
            expected_teams,
            final_teams,
            "Should not show teams until league complete",
        )

    def assertFirstRoundSingleDropoutFromFirstMatch(self, teams):
        positions = OrderedDict()
        positions['ABC'] = 1
        positions['CDE'] = 2
        positions['EFG'] = 3
        positions['GHI'] = 4
        positions['IJK'] = 5
        positions['KLM'] = 6
        positions['MNO'] = 7
        positions['OPQ'] = 8
        positions['RST'] = 9

        # Fake a couple of league matches
        matches = [{}, {}]
        scheduler = get_scheduler(matches, positions=positions, teams=teams)

        def seeder(n_teams, *args):
            self.assertEqual(8, n_teams, "Wrong number of teams")
            return [[0, 1, 2, 3], [4, 5, 6, 7]]

        # Mock the random (even thought it's not really random)
        scheduler.R = mock.Mock()
        # Mock the seeder to make it less interesting
        with mock_first_round_seeding(side_effect=seeder):
            scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds
        period = scheduler.period

        self.assertEqual(2, len(knockout_rounds), "Should be semis and finals")
        semis = knockout_rounds[0]

        self.assertEqual(2, len(semis), "Should be two semis")
        semi_0 = semis[0]
        semi_0_teams = semi_0.teams
        # Thanks to our mocking of the seeder...
        expected_0_teams = list(positions.keys())[1:5]  # 0th team has dropped out

        self.assertEqual(2, semi_0.num, "Match number should carry on above league matches")
        self.assertEqual(MatchType.knockout, semi_0.type)
        self.assertEqual(expected_0_teams, semi_0_teams)
        semi_0_name = semi_0.display_name
        self.assertEqual("Semi 1 (#2)", semi_0_name)   # labelling starts at 1

        period_matches = period.matches
        expected_matches = [{'A': m} for r in knockout_rounds for m in r]

        self.assertEqual(expected_matches, period_matches)
        final = period_matches[2]['A']
        final_teams = final.teams

        self.assertEqual([UNKNOWABLE_TEAM] * 4, final_teams)

    def test_first_round_early_dropout_from_first_match(self):
        teams = defaultdict(lambda: Team(None, None, False, None))
        # dropped out after the first match
        teams['ABC'] = Team(None, None, False, 0)
        self.assertFirstRoundSingleDropoutFromFirstMatch(teams)

    def test_first_round_late_dropout_from_first_match(self):
        teams = defaultdict(lambda: Team(None, None, False, None))
        # dropped out after the leagues
        teams['ABC'] = Team(None, None, False, 1)
        self.assertFirstRoundSingleDropoutFromFirstMatch(teams)

    def assertFirstRoundSingleDropoutFromSecondMatch(self, teams):
        positions = OrderedDict()
        positions['ABC'] = 1
        positions['CDE'] = 2
        positions['EFG'] = 3
        positions['GHI'] = 4
        positions['IJK'] = 5
        positions['KLM'] = 6
        positions['MNO'] = 7
        positions['OPQ'] = 8
        positions['RST'] = 9

        # Fake a couple of league matches
        matches = [{}, {}]
        scheduler = get_scheduler(matches, positions=positions, teams=teams)

        def seeder(n_teams, *args):
            self.assertEqual(8, n_teams, "Wrong number of teams")
            return [[0, 1, 2, 3], [4, 5, 6, 7]]

        # Mock the random (even thought it's not really random)
        scheduler.R = mock.Mock()
        # Mock the seeder to make it less interesting
        with mock_first_round_seeding(side_effect=seeder):
            scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds
        period = scheduler.period

        self.assertEqual(2, len(knockout_rounds), "Should be semis and finals")
        semis = knockout_rounds[0]

        self.assertEqual(2, len(semis), "Should be two semis")
        semi_0 = semis[0]
        semi_0_teams = semi_0.teams
        # Thanks to our mocking of the seeder...
        expected_0_teams = list(positions.keys())[:4]  # 5th team has dropped out

        self.assertEqual(2, semi_0.num, "Match number should carry on above league matches")
        self.assertEqual(MatchType.knockout, semi_0.type)
        self.assertEqual(expected_0_teams, semi_0_teams)
        semi_0_name = semi_0.display_name
        self.assertEqual("Semi 1 (#2)", semi_0_name)  # labelling starts at 1

        semi_1 = semis[1]
        semi_1_teams = semi_1.teams
        # Thanks to our mocking of the seeder...
        expected_1_teams = list(positions.keys())[5:]  # 5th team has dropped out

        self.assertEqual(3, semi_1.num, "Match number should carry on above league matches")
        self.assertEqual(MatchType.knockout, semi_1.type)
        self.assertEqual(expected_1_teams, semi_1_teams)
        semi_1_name = semi_1.display_name
        self.assertEqual("Semi 2 (#3)", semi_1_name)  # labelling starts at 1

        period_matches = period.matches
        expected_matches = [{'A': m} for r in knockout_rounds for m in r]

        self.assertEqual(expected_matches, period_matches)
        final = period_matches[2]['A']
        final_teams = final.teams

        self.assertEqual(final_teams, [UNKNOWABLE_TEAM] * 4)

    def test_first_round_early_dropout_from_second_match(self):
        teams = defaultdict(lambda: Team(None, None, False, None))
        # dropped out after the first match
        teams['IJK'] = Team(None, None, False, 0)
        self.assertFirstRoundSingleDropoutFromSecondMatch(teams)

    def test_first_round_late_dropout_from_second_match(self):
        teams = defaultdict(lambda: Team(None, None, False, None))
        # dropped out after the leagues
        teams['IJK'] = Team(None, None, False, 1)
        self.assertFirstRoundSingleDropoutFromSecondMatch(teams)

    def test_timings_no_delays(self):
        positions = OrderedDict()
        for i in range(16):
            positions[f'team-{i}'] = i

        scheduler = get_scheduler(positions=positions)
        scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds
        num_rounds = len(knockout_rounds)

        self.assertEqual(3, num_rounds, "Should be quarters, semis and finals")

        start_times = [m['A'].start_time for m in scheduler.period.matches]

        expected_times = [
            # Quarter finals
            datetime(2014, 3, 27, 13, 0),
            datetime(2014, 3, 27, 13, 5),
            datetime(2014, 3, 27, 13, 10),
            datetime(2014, 3, 27, 13, 15),

            # 30 second gap

            # Semi finals
            datetime(2014, 3, 27, 13, 20, 30),
            datetime(2014, 3, 27, 13, 25, 30),

            # 30 second gap
            # bonus 12 second gap

            # Final
            datetime(2014, 3, 27, 13, 31, 12),
        ]

        self.assertEqual(expected_times, start_times, "Wrong start times")

    def test_timings_with_delays(self):
        positions = OrderedDict()
        for i in range(16):
            positions[f'team-{i}'] = i

        delays = [
            Delay(
                time=datetime(2014, 3, 27, 13, 2),
                delay=timedelta(minutes=5),
            ),
            Delay(
                time=datetime(2014, 3, 27, 13, 12),
                delay=timedelta(minutes=5),
            ),
        ]

        scheduler = get_scheduler(positions=positions, delays=delays)
        scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds
        num_rounds = len(knockout_rounds)

        self.assertEqual(3, num_rounds, "Should be quarters, semis and finals")

        start_times = [m['A'].start_time for m in scheduler.period.matches]

        expected_times = [
            # Quarter finals
            datetime(2014, 3, 27, 13, 0),
            datetime(2014, 3, 27, 13, 10),  # affected by first delay only
            datetime(2014, 3, 27, 13, 20),  # affected by both delays
            datetime(2014, 3, 27, 13, 25),

            # 30 second gap

            # Semi finals
            datetime(2014, 3, 27, 13, 30, 30),
            datetime(2014, 3, 27, 13, 35, 30),

            # 30 second gap
            # bonus 12 second gap

            # Final
            datetime(2014, 3, 27, 13, 41, 12),
        ]

        self.assertEqual(expected_times, start_times, "Wrong start times")

    def test_timings_with_delays_during_gaps(self):
        positions = OrderedDict()
        for i in range(16):
            positions[f'team-{i}'] = i

        delays = [
            Delay(
                time=datetime(2014, 3, 27, 13, 20, 15),
                delay=timedelta(minutes=5),
            ),
            Delay(
                time=datetime(2014, 3, 27, 13, 36),
                delay=timedelta(minutes=5),
            ),
        ]

        scheduler = get_scheduler(positions=positions, delays=delays)
        scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds
        num_rounds = len(knockout_rounds)

        self.assertEqual(3, num_rounds, "Should be quarters, semis and finals")

        start_times = [m['A'].start_time for m in scheduler.period.matches]

        expected_times = [
            # Quarter finals
            datetime(2014, 3, 27, 13, 0),
            datetime(2014, 3, 27, 13, 5),
            datetime(2014, 3, 27, 13, 10),
            datetime(2014, 3, 27, 13, 15),

            # 30 second gap
            # first delay

            # Semi finals
            datetime(2014, 3, 27, 13, 25, 30),
            datetime(2014, 3, 27, 13, 30, 30),

            # 30 second gap
            # bonus 12 second gap

            # Final
            datetime(2014, 3, 27, 13, 41, 12),
        ]

        self.assertEqual(expected_times, start_times, "Wrong start times")
