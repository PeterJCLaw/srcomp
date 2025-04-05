import unittest
from collections import OrderedDict
from datetime import datetime, timedelta
from unittest import mock

from sr.comp.knockout_scheduler import StaticScheduler, UNKNOWABLE_TEAM
from sr.comp.knockout_scheduler.static_scheduler import (
    InvalidReferenceError,
    InvalidSeedError,
    parse_team_ref,
    WrongNumberOfTeamsError,
)
from sr.comp.match_period import Match, MatchType
from sr.comp.teams import Team

from .factories import build_match

TLAs = ['AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG', 'HHH', 'III', 'JJJ']


def get_four_team_config():
    return {
        'teams_per_arena': 4,
        'matches': {
            0: {
                0: {
                    'arena': 'A',
                    'display_name': "Qualifier 1",
                    'start_time': datetime(2014, 4, 27, 14, 30),
                    'teams': ['S3', 'S5', 'S8', 'S10'],
                },
                1: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 14, 35),
                    'teams': ['S4', 'S6', 'S7', 'S9'],
                },
            },
            1: {
                0: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 14, 45),
                    'teams': ['S2', '000', '002', '011'],
                },
                1: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 14, 50),
                    'teams': ['S1', '001', '010', '012'],
                },
            },
            2: {
                0: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 15, 0),
                    'teams': ['100', '101', '110', '111'],
                },
            },
        },
    }


def get_two_team_config():
    return {
        'teams_per_arena': 2,
        'matches': {
            0: {
                0: {
                    'arena': 'A',
                    'display_name': "Qualifier 1",
                    'start_time': datetime(2014, 4, 27, 14, 30),
                    'teams': ['S3', 'S5'],
                },
                1: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 14, 35),
                    'teams': ['S4', 'S6'],
                },
            },
            1: {
                0: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 14, 45),
                    'teams': ['S1', '000'],
                },
                1: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 14, 50),
                    'teams': ['S2', '010'],
                },
            },
            2: {
                0: {
                    'arena': 'A',
                    'start_time': datetime(2014, 4, 27, 15, 0),
                    'teams': ['100', '110'],
                },
            },
        },
    }


def get_scheduler(
    matches_config,
    matches=None,
    positions=None,
    knockout_positions=None,
    league_game_points=None,
    delays=None,
    teams=None,
):
    matches = matches or []
    delays = delays or []
    match_duration = timedelta(minutes=5)
    league_game_points = league_game_points or {}
    knockout_positions = knockout_positions or {}

    if not positions:
        positions = OrderedDict()
        positions['AAA'] = 1
        positions['BBB'] = 2
        positions['CCC'] = 3
        positions['DDD'] = 4
        positions['EEE'] = 5
        positions['FFF'] = 6
        positions['GGG'] = 7
        positions['HHH'] = 8
        positions['III'] = 9
        positions['JJJ'] = 10

    if sorted(positions.keys()) != TLAs:
        raise ValueError("Must use common TLAs")

    if teams is None:
        teams = {x: Team(x, x, False, None) for x in positions.keys()}

    mock_n_matches = mock.Mock(side_effect=lambda: len(matches))
    league_schedule = mock.Mock(
        matches=matches,
        delays=delays,
        match_duration=match_duration,
        n_matches=mock_n_matches,
    )
    league_scores = mock.Mock(positions=positions, game_points=league_game_points)
    knockout_scores = mock.Mock(resolved_positions=knockout_positions)
    scores = mock.Mock(league=league_scores, knockout=knockout_scores)

    num_teams_per_arena = matches_config.pop('teams_per_arena')

    period_config = {
        "description": "A description of the period",
        "start_time":   datetime(2014, 3, 27, 13),  # noqa:E241
        "end_time":     datetime(2014, 3, 27, 17, 30),  # noqa:E241
    }
    config = {
        'match_periods': {'knockout': [period_config]},
        'static_knockout': matches_config,
    }
    arenas = ['A']

    scheduler = StaticScheduler(
        league_schedule,
        scores,
        arenas,
        num_teams_per_arena,
        teams,
        config,
    )
    return scheduler


def build_5_matches(places, *, first_match_number=0):
    if len(places) != 5:
        raise ValueError("Bad list of team places")

    names = [
        "Qualifier 1 (#{})",
        "Quarter 2 (#{})",
        "Semi 1 (#{})",
        "Semi 2 (#{})",
        "Final (#{})",
    ]
    times = [
        (datetime(2014, 4, 27, 14, 30), datetime(2014, 4, 27, 14, 35)),
        (datetime(2014, 4, 27, 14, 35), datetime(2014, 4, 27, 14, 40)),
        (datetime(2014, 4, 27, 14, 45), datetime(2014, 4, 27, 14, 50)),
        (datetime(2014, 4, 27, 14, 50), datetime(2014, 4, 27, 14, 55)),
        (datetime(2014, 4, 27, 15, 0), datetime(2014, 4, 27, 15, 5)),
    ]

    matches = [
        Match(idx, name.format(idx), 'A', teams, start, end, MatchType.knockout, True)
        for (idx, name), (start, end), teams in zip(
            enumerate(names, start=first_match_number),
            times,
            places,
        )
    ]

    # Final has different resolution expectations
    matches[-1] = matches[-1]._replace(use_resolved_ranking=False)

    return [{'A': match} for match in matches]


class StaticKnockoutSchedulerTests(unittest.TestCase):
    def assertMatches(self, expected_matches, **kwargs):
        scheduler = get_scheduler(**kwargs)
        scheduler.add_knockouts()

        period = scheduler.period

        for i, e in enumerate(expected_matches):
            a = period.matches[i]

            self.assertEqual(e, a, f"Match {i} in the knockouts")

    def assertParseInvalidReference(self, value: str) -> None:
        with self.assertRaises(InvalidReferenceError):
            parse_team_ref(value)

    def assertParseReference(self, expected: tuple[int, int, int], value: str) -> None:
        self.assertEqual(
            expected,
            parse_team_ref(value),
            f"Wrong result from parsing {value!r}",
        )

    def assertInvalidReference(self, value, matches=()):
        config = get_four_team_config()

        config['matches'][1][0]['teams'][0] = value

        self.assertInvalidSchedule(config, InvalidReferenceError, matches)

    def assertInvalidSeed(self, value, matches=()):
        config = get_four_team_config()

        config['matches'][1][0]['teams'][0] = value

        self.assertInvalidSchedule(config, InvalidSeedError, matches)

    def assertInvalidSchedule(self, config, exception_type, matches=()):
        with self.assertRaises(exception_type):
            scheduler = get_scheduler(
                matches_config=config,
                matches=matches,
            )

            scheduler.add_knockouts()

    def test_four_teams_before(self):
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{'A': Match(
            0,
            "Match 0",
            'A',
            [],
            datetime(2014, 4, 27, 12, 30),
            datetime(2014, 4, 27, 12, 35),
            MatchType.league,
            use_resolved_ranking=False,
        )}]

        expected = build_5_matches(
            places=[[UNKNOWABLE_TEAM] * 4] * 5,
            first_match_number=1,
        )

        self.assertMatches(
            expected,
            matches_config=get_four_team_config(),
            matches=league_matches,
        )

    def test_four_teams_start(self):
        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB'] + [UNKNOWABLE_TEAM] * 3,
            ['AAA'] + [UNKNOWABLE_TEAM] * 3,
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=get_four_team_config(),
        )

    def test_four_teams_start_only_progressing_winner_from_quarters(self):
        config = get_four_team_config()

        semis = config['matches'][1]
        semis[0]['teams'][-1] = None
        semis[1]['teams'][-1] = None

        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB', UNKNOWABLE_TEAM, UNKNOWABLE_TEAM, None],
            ['AAA', UNKNOWABLE_TEAM, UNKNOWABLE_TEAM, None],
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=config,
        )

    def test_four_teams_with_dropout_part_way_through(self):
        LAST_QUARTER_FINAL_MATCH_NUM = 1

        teams = {x: Team(x, x, False, None) for x in TLAs}
        teams['BBB'] = Team(
            'BBB',
            'BBB',
            False,
            dropped_out_after=LAST_QUARTER_FINAL_MATCH_NUM,
        )

        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB'] + [UNKNOWABLE_TEAM] * 3,
            ['AAA'] + [UNKNOWABLE_TEAM] * 3,
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=get_four_team_config(),
            teams=teams,
        )

    def test_four_teams_with_dropout_before_start(self):
        teams = {x: Team(x, x, False, None) for x in TLAs}
        teams['BBB'] = Team('BBB', 'BBB', False, dropped_out_after=-1)

        config = get_four_team_config()
        qualifier_teams = config['matches'][0][0]['teams']

        self.assertEqual('S10', qualifier_teams[-1], "Setup self-check failed!")
        qualifier_teams[-1] = None

        expected_matches = build_5_matches([
            ['DDD', 'FFF', 'III', None],
            ['EEE', 'GGG', 'HHH', 'JJJ'],
            ['CCC'] + [UNKNOWABLE_TEAM] * 3,
            ['AAA'] + [UNKNOWABLE_TEAM] * 3,
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=config,
            teams=teams,
        )

    def test_four_teams_partial_1(self):
        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB', 'JJJ', 'EEE', UNKNOWABLE_TEAM],
            ['AAA', 'HHH', UNKNOWABLE_TEAM, UNKNOWABLE_TEAM],
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=get_four_team_config(),
            knockout_positions={
                # QF 1
                ('A', 0): OrderedDict([
                    ('JJJ', 1),
                    ('HHH', 2),
                    ('EEE', 3),
                    ('CCC', 4),
                ]),
            },
        )

    def test_four_teams_partial_2(self):
        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB', 'JJJ', 'EEE', 'GGG'],
            ['AAA', 'HHH', 'III', 'FFF'],
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=get_four_team_config(),
            knockout_positions={
                # QF 1
                ('A', 0): OrderedDict([
                    ('JJJ', 1),
                    ('HHH', 2),
                    ('EEE', 3),
                    ('CCC', 4),
                ]),
                # QF 2
                ('A', 1): OrderedDict([
                    ('III', 1),
                    ('GGG', 2),
                    ('FFF', 3),
                    ('DDD', 4),
                ]),
            },
        )

    def test_two_teams_before(self):
        league_matches = [{'A': Match(
            0,
            "Match 0",
            'A',
            [],
            datetime(2014, 4, 27, 12, 30),
            datetime(2014, 4, 27, 12, 35),
            MatchType.league,
            use_resolved_ranking=False,
        )}]

        expected = build_5_matches(
            places=[[UNKNOWABLE_TEAM] * 2] * 5,
            first_match_number=1,
        )

        self.assertMatches(
            expected,
            matches_config=get_two_team_config(),
            matches=league_matches,
        )

    def test_two_teams_start(self):
        expected_matches = build_5_matches([
            ['CCC', 'EEE'],
            ['DDD', 'FFF'],
            ['AAA', UNKNOWABLE_TEAM],
            ['BBB', UNKNOWABLE_TEAM],
            [UNKNOWABLE_TEAM] * 2,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=get_two_team_config(),
        )

    def test_two_teams_partial_1(self):
        expected_matches = build_5_matches([
            ['CCC', 'EEE'],
            ['DDD', 'FFF'],
            ['AAA', 'EEE'],
            ['BBB', UNKNOWABLE_TEAM],
            [UNKNOWABLE_TEAM] * 2,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=get_two_team_config(),
            knockout_positions={
                # QF 1
                ('A', 0): OrderedDict([
                    ('EEE', 1),
                    ('CCC', 2),
                ]),
            },
        )

    def test_two_teams_partial_2(self):
        expected_matches = build_5_matches([
            ['CCC', 'EEE'],
            ['DDD', 'FFF'],
            ['AAA', 'EEE'],
            ['BBB', 'DDD'],
            [UNKNOWABLE_TEAM] * 2,
        ])

        self.assertMatches(
            expected_matches,
            matches_config=get_two_team_config(),
            knockout_positions={
                # QF 1
                ('A', 0): OrderedDict([
                    ('EEE', 1),
                    ('CCC', 2),
                ]),
                # QF 2
                ('A', 1): OrderedDict([
                    ('DDD', 1),
                    ('FFF', 2),
                ]),
            },
        )

    def test_parse_team_ref_invalid_short(self):
        self.assertParseInvalidReference('00')

    def test_parse_team_ref_invalid_long(self):
        self.assertParseInvalidReference('00')

    def test_parse_team_ref_invalid_not_digits(self):
        self.assertParseInvalidReference('bee')

    def test_parse_team_ref_invalid_rmp_not_digits(self):
        self.assertParseInvalidReference('R_M_P_')

    def test_parse_team_ref_legacy(self):
        self.assertParseReference(
            (1, 2, 3),
            '123',
        )

    def test_parse_team_ref_rmp(self):
        self.assertParseReference(
            (1, 2, 3),
            'R1M2P3',
        )

    def test_parse_team_ref_rmp_long(self):
        self.assertParseReference(
            (10, 20, 30),
            'R10M20P30',
        )

    def test_improper_position_reference(self):
        self.assertInvalidReference('00')

    def test_invalid_position_reference(self):
        self.assertInvalidReference('005')

    def test_invalid_match_reference(self):
        self.assertInvalidReference('050')

    def test_invalid_round_reference(self):
        self.assertInvalidReference('500')

    def test_invalid_seed_reference_low(self):
        self.assertInvalidSeed('S0')

    def test_invalid_seed_reference_high(self):
        self.assertInvalidSeed('S9999')

    def test_invalid_reference_other_text(self):
        self.assertInvalidReference('bees')

    def test_invalid_position_reference_incomplete_league(self):
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{'A': build_match(arena='A')}]
        self.assertInvalidReference('005', matches=league_matches)

    def test_invalid_match_reference_incomplete_league(self):
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{'A': build_match(arena='A')}]
        self.assertInvalidReference('050', matches=league_matches)

    def test_invalid_round_reference_incomplete_league(self):
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{'A': build_match(arena='A')}]
        self.assertInvalidReference('500', matches=league_matches)

    def test_invalid_seed_reference_low_incomplete_league(self):
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{'A': build_match(arena='A')}]
        self.assertInvalidSeed('S0', matches=league_matches)

    def test_invalid_seed_reference_high_incomplete_league(self):
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{'A': build_match(arena='A')}]
        self.assertInvalidSeed('S9999', matches=league_matches)

    def test_too_few_teams_first_round(self):
        config = get_four_team_config()

        config['matches'][0][0]['teams'].pop()

        self.assertInvalidSchedule(config, WrongNumberOfTeamsError)

    def test_too_few_teams_second_round(self):
        config = get_four_team_config()

        config['matches'][1][0]['teams'].pop()

        self.assertInvalidSchedule(config, WrongNumberOfTeamsError)

    def test_too_few_teams_third_round(self):
        config = get_four_team_config()

        config['matches'][2][0]['teams'].pop()

        self.assertInvalidSchedule(config, WrongNumberOfTeamsError)

    def test_too_many_teams_first_round(self):
        config = get_four_team_config()

        config['matches'][0][0]['teams'].append('S1')

        self.assertInvalidSchedule(config, WrongNumberOfTeamsError)

    def test_too_many_teams_second_round(self):
        config = get_four_team_config()

        config['matches'][1][0]['teams'].append('S1')

        self.assertInvalidSchedule(config, WrongNumberOfTeamsError)

    def test_too_many_teams_third_round(self):
        config = get_four_team_config()

        config['matches'][2][0]['teams'].append('S1')

        self.assertInvalidSchedule(config, WrongNumberOfTeamsError)
