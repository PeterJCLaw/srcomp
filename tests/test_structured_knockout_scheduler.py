from __future__ import annotations

import itertools
import unittest
from collections import OrderedDict
from collections.abc import Collection, Mapping, Sequence
from datetime import datetime, timedelta
from unittest import mock

from league_ranker import RankedPosition

from sr.comp.knockout_scheduler import StructuredScheduler, UNKNOWABLE_TEAM
from sr.comp.knockout_scheduler.base_scheduler import (
    DEFAULT_KNOCKOUT_BRACKET_NAME,
)
from sr.comp.knockout_scheduler.exceptions import (
    InvalidReferenceError,
    InvalidSeedError,
    WrongNumberOfTeamsError,
)
from sr.comp.knockout_scheduler.structured_scheduler import (
    StructuredKnockoutScheduleData,
)
from sr.comp.match_period import (
    Delay,
    KnockoutMatch,
    Match,
    MatchSlot,
    MatchType,
)
from sr.comp.scores import LeaguePosition, LeaguePositions
from sr.comp.teams import Team
from sr.comp.types import (
    ArenaName,
    GamePoints,
    MatchId,
    MatchNumber,
    MatchPeriodData,
    ScheduleKnockoutRoundSpacingData,
    StructuredKnockoutData,
    StructuredKnockoutRoundData,
    StructuredMatchTeamPositionReference,
    StructuredSeedReference,
    TLA,
)

from .factories import build_match, FakeSchedule

TLAs = ['AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG', 'HHH', 'III', 'JJJ']

ARENA_A = ArenaName('A')
ARENA_B = ArenaName('B')


def _team_ref(
    round: int,  # noqa: A002
    slot: int,
    arena: str,
    position: int,
) -> StructuredMatchTeamPositionReference:
    return {
        'round': round,
        'slot': slot,
        'arena': ArenaName(arena),
        'position': position,
    }


def get_round_spacing_data() -> ScheduleKnockoutRoundSpacingData:
    return {
        'default': {
            'delay_flex': 0,
            'minimum': 300,
            'nominal': 300,
        },
        'overrides': {
            -1: {
                'delay_flex': 300,
                'minimum': 300,
                'nominal': 600,
            },
        },
    }


def get_four_team_structure() -> tuple[int, StructuredKnockoutData]:
    rounds: Mapping[int, StructuredKnockoutRoundData] = {
        0: {
            'match_slots': {
                0: {
                    ARENA_A: {
                        'display_name': "Qualifier A",
                        'teams': [
                            {'seed': 3},
                            {'seed': 5},
                            {'seed': 8},
                            {'seed': 10},
                        ],
                    },
                    ARENA_B: {
                        'display_name': "Qualifier B",
                        'teams': [
                            {'seed': 4},
                            {'seed': 6},
                            {'seed': 7},
                            {'seed': 9},
                        ],
                    },
                },
            },
        },
        1: {
            'match_slots': {
                0: {
                    ARENA_A: {
                        'display_name': "Semi A 0",
                        'teams': [
                            {'seed': 2},
                            _team_ref(round=0, slot=0, arena=ARENA_A, position=0),
                            _team_ref(round=0, slot=0, arena=ARENA_A, position=2),
                            _team_ref(round=0, slot=0, arena=ARENA_B, position=1),
                        ],
                    },
                },
                1: {
                    ARENA_A: {
                        'display_name': "Semi A 1",
                        'teams': [
                            {'seed': 1},
                            _team_ref(round=0, slot=0, arena=ARENA_A, position=1),
                            _team_ref(round=0, slot=0, arena=ARENA_B, position=0),
                            _team_ref(round=0, slot=0, arena=ARENA_B, position=2),
                        ],
                    },
                },
            },
        },
        2: {
            'match_slots': {
                0: {
                    ARENA_A: {
                        'teams': [
                            _team_ref(round=1, slot=0, arena=ARENA_A, position=0),
                            _team_ref(round=1, slot=0, arena=ARENA_A, position=1),
                            _team_ref(round=1, slot=1, arena=ARENA_A, position=0),
                            _team_ref(round=1, slot=1, arena=ARENA_A, position=1),
                        ],
                    },
                },
            },
        },
    }

    return 4, {'rounds': rounds}


def get_two_team_structure() -> tuple[int, StructuredKnockoutData]:
    rounds: Mapping[int, StructuredKnockoutRoundData] = {
        0: {
            'match_slots': {
                0: {
                    ARENA_A: {
                        'display_name': "Qualifier A",
                        'teams': [
                            {'seed': 3},
                            {'seed': 5},
                        ],
                    },
                    ARENA_B: {
                        'display_name': "Qualifier B",
                        'teams': [
                            {'seed': 4},
                            {'seed': 6},
                        ],
                    },
                },
            },
        },
        1: {
            'match_slots': {
                0: {
                    ARENA_A: {
                        'display_name': "Semi A 0",
                        'teams': [
                            {'seed': 1},
                            _team_ref(round=0, slot=0, arena=ARENA_A, position=0),
                        ],
                    },
                },
                1: {
                    ARENA_A: {
                        'display_name': "Semi A 1",
                        'teams': [
                            {'seed': 2},
                            _team_ref(round=0, slot=0, arena=ARENA_B, position=0),
                        ],
                    },
                },
            },
        },
        2: {
            'match_slots': {
                0: {
                    ARENA_A: {
                        'teams': [
                            _team_ref(round=1, slot=0, arena=ARENA_A, position=0),
                            _team_ref(round=1, slot=1, arena=ARENA_A, position=0),
                        ],
                    },
                },
            },
        },
    }

    return 2, {'rounds': rounds}


def get_scheduler(
    structure_data: tuple[int, StructuredKnockoutData],
    round_spacing: ScheduleKnockoutRoundSpacingData | None = None,
    matches: Collection[Mapping[ArenaName, Match]] | None = None,
    positions: LeaguePositions | None = None,
    knockout_positions: Mapping[MatchId, Mapping[TLA, RankedPosition]] | None = None,
    league_game_points: dict[MatchId, Mapping[TLA, GamePoints]] | None = None,
    delays: list[Delay] | None = None,
    teams: dict[TLA, Team] | None = None,
) -> StructuredScheduler:
    round_spacing = round_spacing or get_round_spacing_data()
    matches = matches or []
    delays = delays or []
    match_duration = timedelta(minutes=5)
    league_game_points = league_game_points or {}
    knockout_positions = knockout_positions or {}

    if not positions:
        positions = OrderedDict()
        positions[TLA('AAA')] = LeaguePosition(1)
        positions[TLA('BBB')] = LeaguePosition(2)
        positions[TLA('CCC')] = LeaguePosition(3)
        positions[TLA('DDD')] = LeaguePosition(4)
        positions[TLA('EEE')] = LeaguePosition(5)
        positions[TLA('FFF')] = LeaguePosition(6)
        positions[TLA('GGG')] = LeaguePosition(7)
        positions[TLA('HHH')] = LeaguePosition(8)
        positions[TLA('III')] = LeaguePosition(9)
        positions[TLA('JJJ')] = LeaguePosition(10)

    if sorted(positions.keys()) != TLAs:
        raise ValueError("Must use common TLAs")

    if teams is None:
        teams = {x: Team(x, x, False, None) for x in positions.keys()}

    league_schedule = FakeSchedule(
        matches=[MatchSlot(x) for x in matches],
        delays=delays,
        match_duration=match_duration,
    )
    league_scores = mock.Mock(positions=positions, game_points=league_game_points)
    knockout_scores = mock.Mock(resolved_positions=knockout_positions)
    scores = mock.Mock(league=league_scores, knockout=knockout_scores)

    num_teams_per_arena, structure = structure_data

    period_config: MatchPeriodData = {
        "description": "A description of the period",
        "start_time": datetime(2014, 4, 27, 14, 30),
        "end_time": datetime(2014, 4, 27, 17, 30),
    }
    config: StructuredKnockoutScheduleData = {
        'match_periods': {'knockout': [period_config]},
        'brackets': (),
        'structure': structure,
        'round_spacing': round_spacing,
    }
    arenas = [ARENA_A, ARENA_B]

    scheduler = StructuredScheduler(
        league_schedule,
        scores,
        arenas,
        num_teams_per_arena,
        teams,
        config,
    )
    return scheduler


def build_5_matches(
    places: Sequence[Collection[TLA | str | None]],
    *,
    first_match_number: int = 0,
) -> list[MatchSlot]:
    if len(places) != 5:
        raise ValueError("Bad list of team places")

    match_numbers = iter(itertools.count(start=first_match_number))

    def _convert_teams(teams: Collection[TLA | str | None]) -> list[TLA | None]:
        return [TLA(x) if x is not None else None for x in teams]

    return [
        MatchSlot({
            ARENA_A: KnockoutMatch(
                MatchNumber(n := next(match_numbers)),
                f"Qualifier A (#{n})",
                ARENA_A,
                _convert_teams(places[0]),
                start_time=datetime(2014, 4, 27, 14, 30),
                end_time=datetime(2014, 4, 27, 14, 35),
                type=MatchType.knockout,
                use_resolved_ranking=True,
                knockout_bracket=DEFAULT_KNOCKOUT_BRACKET_NAME,
            ),
            ARENA_B: KnockoutMatch(
                MatchNumber(n),
                f"Qualifier B (#{n})",
                ARENA_B,
                _convert_teams(places[1]),
                start_time=datetime(2014, 4, 27, 14, 30),
                end_time=datetime(2014, 4, 27, 14, 35),
                type=MatchType.knockout,
                use_resolved_ranking=True,
                knockout_bracket=DEFAULT_KNOCKOUT_BRACKET_NAME,
            ),
        }),
        MatchSlot({
            ARENA_A: KnockoutMatch(
                MatchNumber(n := next(match_numbers)),
                f"Semi A 0 (#{n})",
                ARENA_A,
                _convert_teams(places[2]),
                start_time=datetime(2014, 4, 27, 14, 40),
                end_time=datetime(2014, 4, 27, 14, 45),
                type=MatchType.knockout,
                use_resolved_ranking=True,
                knockout_bracket=DEFAULT_KNOCKOUT_BRACKET_NAME,
            ),
        }),
        MatchSlot({
            ARENA_A: KnockoutMatch(
                MatchNumber(n := next(match_numbers)),
                f"Semi A 1 (#{n})",
                ARENA_A,
                _convert_teams(places[3]),
                start_time=datetime(2014, 4, 27, 14, 45),
                end_time=datetime(2014, 4, 27, 14, 50),
                type=MatchType.knockout,
                use_resolved_ranking=True,
                knockout_bracket=DEFAULT_KNOCKOUT_BRACKET_NAME,
            ),
        }),
        MatchSlot({
            ARENA_A: KnockoutMatch(
                MatchNumber(n := next(match_numbers)),
                f"Final (#{n})",
                ARENA_A,
                _convert_teams(places[4]),
                start_time=datetime(2014, 4, 27, 15, 0),
                end_time=datetime(2014, 4, 27, 15, 5),
                type=MatchType.knockout,
                use_resolved_ranking=False,
                knockout_bracket=DEFAULT_KNOCKOUT_BRACKET_NAME,
            ),
        }),
    ]


class StaticKnockoutSchedulerTests(unittest.TestCase):
    maxDiff = None

    def assertMatches(
        self,
        expected_matches: Collection[Mapping[ArenaName, Match]],
        structure_data: tuple[int, StructuredKnockoutData],
        round_spacing: ScheduleKnockoutRoundSpacingData | None = None,
        matches: Collection[Mapping[ArenaName, Match]] | None = None,
        positions: LeaguePositions | None = None,
        knockout_positions: Mapping[MatchId, Mapping[TLA, RankedPosition]] | None = None,
        league_game_points: dict[MatchId, Mapping[TLA, GamePoints]] | None = None,
        delays: list[Delay] | None = None,
        teams: dict[TLA, Team] | None = None,
    ) -> None:
        scheduler = get_scheduler(
            structure_data=structure_data,
            round_spacing=round_spacing,
            matches=matches,
            positions=positions,
            knockout_positions=knockout_positions,
            league_game_points=league_game_points,
            delays=delays,
            teams=teams,
        )
        scheduler.add_knockouts()

        period = scheduler.period

        self.assertEqual(
            expected_matches,
            period.matches,
            "Wrong knockout matches",
        )

    def assertInvalidReference(
        self,
        value: StructuredMatchTeamPositionReference,
        matches: Collection[Mapping[ArenaName, Match]] = (),
    ) -> None:
        n_teams, config = get_four_team_structure()

        match_info = config['rounds'][1]['match_slots'][0][ARENA_A]
        match_info['teams'][0] = value

        self.assertInvalidSchedule(n_teams, config, InvalidReferenceError, matches)

    def assertInvalidSeed(
        self,
        value: StructuredSeedReference,
        matches: Collection[Mapping[ArenaName, Match]] = (),
    ) -> None:
        n_teams, config = get_four_team_structure()

        match_info = config['rounds'][1]['match_slots'][0][ARENA_A]
        match_info['teams'][0] = value

        self.assertInvalidSchedule(n_teams, config, InvalidSeedError, matches)

    def assertInvalidSchedule(
        self,
        num_teams_per_arena: int,
        structure: StructuredKnockoutData,
        exception_type: type[Exception],
        matches: Collection[Mapping[ArenaName, Match]] = (),
        round_spacing: ScheduleKnockoutRoundSpacingData | None = None,
    ) -> None:
        with self.assertRaises(exception_type):
            scheduler = get_scheduler(
                (num_teams_per_arena, structure),
                round_spacing=round_spacing,
                matches=matches,
            )

            scheduler.add_knockouts()

    def test_four_teams_before(self) -> None:
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{ARENA_A: build_match(arena=ARENA_A)}]

        expected = build_5_matches(
            places=[[UNKNOWABLE_TEAM] * 4] * 5,
            first_match_number=1,
        )

        self.assertMatches(
            expected,
            structure_data=get_four_team_structure(),
            matches=league_matches,
        )

    def test_four_teams_start(self) -> None:
        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB'] + [UNKNOWABLE_TEAM] * 3,
            ['AAA'] + [UNKNOWABLE_TEAM] * 3,
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            structure_data=get_four_team_structure(),
        )

    def test_four_teams_start_only_progressing_winner_from_quarters(self) -> None:
        n_teams, config = get_four_team_structure()

        semis = config['rounds'][1]['match_slots']
        semis[0][ARENA_A]['teams'][-1] = None
        semis[1][ARENA_A]['teams'][-1] = None

        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB', UNKNOWABLE_TEAM, UNKNOWABLE_TEAM, None],
            ['AAA', UNKNOWABLE_TEAM, UNKNOWABLE_TEAM, None],
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            structure_data=(n_teams, config),
        )

    def test_four_teams_with_dropout_part_way_through(self) -> None:
        LAST_QUARTER_FINAL_MATCH_NUM = MatchNumber(1)

        teams = {TLA(x): Team(TLA(x), x, False, None) for x in TLAs}
        teams[TLA('BBB')] = Team(
            TLA('BBB'),
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
            structure_data=get_four_team_structure(),
            teams=teams,
        )

    def test_four_teams_with_dropout_before_start(self) -> None:
        teams = {TLA(x): Team(TLA(x), x, False, None) for x in TLAs}
        teams[TLA('BBB')] = Team(TLA('BBB'), 'BBB', False, dropped_out_after=MatchNumber(-1))

        n_teams, config = get_four_team_structure()
        qualifier_teams = config['rounds'][0]['match_slots'][0][ARENA_A]['teams']

        self.assertEqual({'seed': 10}, qualifier_teams[-1], "Setup self-check failed!")
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
            structure_data=(n_teams, config),
            teams=teams,
        )

    def test_four_teams_partial_1(self) -> None:
        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB', 'JJJ', 'EEE', UNKNOWABLE_TEAM],
            ['AAA', 'HHH', UNKNOWABLE_TEAM, UNKNOWABLE_TEAM],
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            structure_data=get_four_team_structure(),
            knockout_positions={
                # QF 1
                (ARENA_A, MatchNumber(0)): OrderedDict([
                    ('JJJ', RankedPosition(1)),
                    ('HHH', RankedPosition(2)),
                    ('EEE', RankedPosition(3)),
                    ('CCC', RankedPosition(4)),
                ]),
            },
        )

    def test_four_teams_partial_2(self) -> None:
        expected_matches = build_5_matches([
            ['CCC', 'EEE', 'HHH', 'JJJ'],
            ['DDD', 'FFF', 'GGG', 'III'],
            ['BBB', 'JJJ', 'EEE', 'GGG'],
            ['AAA', 'HHH', 'III', 'FFF'],
            [UNKNOWABLE_TEAM] * 4,
        ])

        self.assertMatches(
            expected_matches,
            structure_data=get_four_team_structure(),
            knockout_positions={
                # QF 1
                (ARENA_A, MatchNumber(0)): OrderedDict([
                    ('JJJ', RankedPosition(1)),
                    ('HHH', RankedPosition(2)),
                    ('EEE', RankedPosition(3)),
                    ('CCC', RankedPosition(4)),
                ]),
                # QF 2
                (ARENA_B, MatchNumber(0)): OrderedDict([
                    ('III', RankedPosition(1)),
                    ('GGG', RankedPosition(2)),
                    ('FFF', RankedPosition(3)),
                    ('DDD', RankedPosition(4)),
                ]),
            },
        )

    def test_two_teams_before(self) -> None:
        league_matches = [{ARENA_A: build_match(arena=ARENA_A)}]

        expected = build_5_matches(
            places=[[UNKNOWABLE_TEAM] * 2] * 5,
            first_match_number=1,
        )

        self.assertMatches(
            expected,
            structure_data=get_two_team_structure(),
            matches=league_matches,
        )

    def test_two_teams_start(self) -> None:
        expected_matches = build_5_matches([
            ['CCC', 'EEE'],
            ['DDD', 'FFF'],
            ['AAA', UNKNOWABLE_TEAM],
            ['BBB', UNKNOWABLE_TEAM],
            [UNKNOWABLE_TEAM] * 2,
        ])

        self.assertMatches(
            expected_matches,
            structure_data=get_two_team_structure(),
        )

    def test_two_teams_partial_1(self) -> None:
        expected_matches = build_5_matches([
            ['CCC', 'EEE'],
            ['DDD', 'FFF'],
            ['AAA', 'EEE'],
            ['BBB', UNKNOWABLE_TEAM],
            [UNKNOWABLE_TEAM] * 2,
        ])

        self.assertMatches(
            expected_matches,
            structure_data=get_two_team_structure(),
            knockout_positions={
                # QF 1
                (ARENA_A, MatchNumber(0)): OrderedDict([
                    ('EEE', RankedPosition(1)),
                    ('CCC', RankedPosition(2)),
                ]),
            },
        )

    def test_two_teams_partial_2(self) -> None:
        expected_matches = build_5_matches([
            ['CCC', 'EEE'],
            ['DDD', 'FFF'],
            ['AAA', 'EEE'],
            ['BBB', 'DDD'],
            [UNKNOWABLE_TEAM] * 2,
        ])

        self.assertMatches(
            expected_matches,
            structure_data=get_two_team_structure(),
            knockout_positions={
                # QF 1
                (ARENA_A, MatchNumber(0)): OrderedDict([
                    ('EEE', RankedPosition(1)),
                    ('CCC', RankedPosition(2)),
                ]),
                # QF 2
                (ARENA_B, MatchNumber(0)): OrderedDict([
                    ('DDD', RankedPosition(1)),
                    ('FFF', RankedPosition(2)),
                ]),
            },
        )

    def test_invalid_position_reference(self) -> None:
        self.assertInvalidReference(
            _team_ref(round=0, slot=0, arena=ARENA_A, position=5),
        )

    def test_invalid_arena_reference_no_such_arena(self) -> None:
        self.assertInvalidReference(
            _team_ref(round=0, slot=0, arena=ArenaName('Missing'), position=0),
        )

    def test_invalid_arena_reference_not_used(self) -> None:
        self.assertInvalidReference(
            _team_ref(round=2, slot=0, arena=ARENA_B, position=0),
        )

    def test_invalid_slot_reference(self) -> None:
        self.assertInvalidReference(
            _team_ref(round=0, slot=5, arena=ARENA_A, position=0),
        )

    def test_invalid_round_reference(self) -> None:
        self.assertInvalidReference(
            _team_ref(round=5, slot=0, arena=ARENA_A, position=0),
        )

    def test_invalid_seed_reference_low(self) -> None:
        self.assertInvalidSeed({'seed': 0})

    def test_invalid_seed_reference_high(self) -> None:
        self.assertInvalidSeed({'seed': 9999})

    def test_invalid_position_reference_incomplete_league(self) -> None:
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{ARENA_A: build_match(arena=ARENA_A)}]
        self.assertInvalidReference(
            _team_ref(round=0, slot=0, arena=ARENA_A, position=5),
            matches=league_matches,
        )

    def test_invalid_match_reference_incomplete_league(self) -> None:
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{ARENA_A: build_match(arena=ARENA_A)}]
        self.assertInvalidReference(
            _team_ref(round=0, slot=5, arena=ARENA_A, position=5),
            matches=league_matches,
        )

    def test_invalid_round_reference_incomplete_league(self) -> None:
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{ARENA_A: build_match(arena=ARENA_A)}]
        self.assertInvalidReference(
            _team_ref(round=5, slot=0, arena=ARENA_A, position=5),
            matches=league_matches,
        )

    def test_invalid_seed_reference_low_incomplete_league(self) -> None:
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{ARENA_A: build_match(arena=ARENA_A)}]
        self.assertInvalidSeed({'seed': 0}, matches=league_matches)

    def test_invalid_seed_reference_high_incomplete_league(self) -> None:
        # Add an un-scored league match so that we don't appear to have played them all
        league_matches = [{ARENA_A: build_match(arena=ARENA_A)}]
        self.assertInvalidSeed({'seed': 9999}, matches=league_matches)

    def test_too_few_teams_first_round(self) -> None:
        n_teams, config = get_four_team_structure()

        config['rounds'][0]['match_slots'][0][ARENA_A]['teams'].pop()

        self.assertInvalidSchedule(n_teams, config, WrongNumberOfTeamsError)

    def test_too_few_teams_second_round(self) -> None:
        n_teams, config = get_four_team_structure()

        config['rounds'][1]['match_slots'][0][ARENA_A]['teams'].pop()

        self.assertInvalidSchedule(n_teams, config, WrongNumberOfTeamsError)

    def test_too_few_teams_third_round(self) -> None:
        n_teams, config = get_four_team_structure()

        config['rounds'][2]['match_slots'][0][ARENA_A]['teams'].pop()

        self.assertInvalidSchedule(n_teams, config, WrongNumberOfTeamsError)

    def test_too_many_teams_first_round(self) -> None:
        n_teams, config = get_four_team_structure()

        config['rounds'][0]['match_slots'][0][ARENA_A]['teams'].append({'seed': 1})

        self.assertInvalidSchedule(n_teams, config, WrongNumberOfTeamsError)

    def test_too_many_teams_second_round(self) -> None:
        n_teams, config = get_four_team_structure()

        config['rounds'][1]['match_slots'][0][ARENA_A]['teams'].append({'seed': 1})

        self.assertInvalidSchedule(n_teams, config, WrongNumberOfTeamsError)

    def test_too_many_teams_third_round(self) -> None:
        n_teams, config = get_four_team_structure()

        config['rounds'][2]['match_slots'][0][ARENA_A]['teams'].append({'seed': 1})

        self.assertInvalidSchedule(n_teams, config, WrongNumberOfTeamsError)

    def test_timings_no_delays(self) -> None:
        scheduler = get_scheduler(get_four_team_structure())
        scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds
        num_rounds = len(knockout_rounds)

        self.assertEqual(3, num_rounds, "Should be quarters, semis and finals")

        start_times = [m[ARENA_A].start_time for m in scheduler.period.matches]

        expected_times = [
            # Quarter finals
            datetime(2014, 4, 27, 14, 30),

            # 5 minute gap

            # Semis
            datetime(2014, 4, 27, 14, 40),
            datetime(2014, 4, 27, 14, 45),

            # 10 minute gap

            # Final
            datetime(2014, 4, 27, 15, 0),
        ]

        self.assertEqual(expected_times, start_times, "Wrong start times")

    def test_timings_with_delays_later_absorbed(self) -> None:
        delays = [
            Delay(
                time=datetime(2014, 4, 27, 14, 32),
                delay=timedelta(minutes=2),
            ),
            Delay(
                time=datetime(2014, 4, 27, 14, 43),
                delay=timedelta(minutes=2),
            ),
        ]

        scheduler = get_scheduler(
            get_four_team_structure(),
            delays=delays,
        )
        scheduler.add_knockouts()

        knockout_rounds = scheduler.knockout_rounds
        num_rounds = len(knockout_rounds)

        self.assertEqual(3, num_rounds, "Should be quarters, semis and finals")

        start_times = [m[ARENA_A].start_time for m in scheduler.period.matches]

        expected_times = [
            # Quarter finals
            datetime(2014, 4, 27, 14, 30),

            # 5 minute gap, no flex, delay carries

            # Semis
            datetime(2014, 4, 27, 14, 42),  # affected by first delay
            datetime(2014, 4, 27, 14, 49),  # affected by both delays

            # 10 minute gap, 5 minutes flex, all time recovered

            # Final
            datetime(2014, 4, 27, 15, 0),
        ]

        self.assertEqual(expected_times, start_times, "Wrong start times")

        self.assertEqual(
            [
                Delay(
                    time=datetime(2014, 4, 27, 14, 32),
                    delay=timedelta(minutes=2),
                ),
                Delay(
                    time=datetime(2014, 4, 27, 14, 43),
                    delay=timedelta(minutes=2),
                ),
                Delay(
                    time=datetime(2014, 4, 27, 14, 54),
                    delay=timedelta(minutes=-4),
                ),
            ],
            scheduler.schedule.delays,
            "Should have updated the schedule with recovered time",
        )

        self.assertEqual(
            timedelta(0),
            sum((x.delay for x in scheduler.schedule.delays), start=timedelta(0)),
            "Final delay should be zero",
        )
