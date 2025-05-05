import datetime
import unittest
from collections import defaultdict, OrderedDict
from datetime import timedelta
from unittest import mock

from sr.comp.knockout_scheduler.base_scheduler import BaseKnockoutScheduler
from sr.comp.teams import Team


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

    mock_n_matches = mock.Mock(side_effect=lambda: len(matches))
    league_schedule = mock.Mock(
        matches=matches,
        delays=delays,
        match_duration=match_duration,
        n_matches=mock_n_matches,
        n_league_matches=mock_n_matches(),
    )
    league_scores = mock.Mock(
        positions=positions,
        game_points=league_game_points,
    )
    knockout_scores = mock.Mock(resolved_positions=knockout_positions)
    scores = mock.Mock(league=league_scores, knockout=knockout_scores)

    period_config = {
        'description': "A description of the period",
        'start_time': datetime.datetime(2014, 3, 27, 13),
        'end_time':   datetime.datetime(2014, 3, 27, 17, 30),  # noqa:E241
    }
    config = {
        'match_periods': {'knockout': [period_config]},
    }
    arenas = ['A']
    if teams is None:
        teams = defaultdict(lambda: Team(None, None, False, None))
    scheduler = BaseKnockoutScheduler(
        league_schedule,
        scores,
        arenas,
        num_teams_per_arena,
        teams,
        config=config,
    )
    return scheduler


class BaseKnockoutSchedulerTests(unittest.TestCase):
    def test_get_seeds_unknowable(self):
        scheduler = get_scheduler(matches=[
            # Fake an unplayed league match
            {},
        ])
        self.assertEqual(
            ['ABC', 'DEF'],
            scheduler._get_seeds(),
        )

    def test_get_seeds_known(self):
        scheduler = get_scheduler()
        self.assertEqual(
            ['ABC', 'DEF'],
            scheduler._get_seeds(),
        )
