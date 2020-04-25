import unittest
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from unittest import mock

from dateutil.tz import tzutc
from league_ranker import calc_positions, calc_ranked_points

from sr.comp.arenas import ArenaName
from sr.comp.match_period import Match, MatchType
from sr.comp.scores import TeamScore
from sr.comp.teams import Team
from sr.comp.types import MatchNumber, TLA
from sr.comp.winners import Award, compute_awards

FINAL_INFO = Match(
    num=MatchNumber(1),
    display_name="Match 1",
    arena=ArenaName('A'),
    teams=[TLA('AAA'), TLA('BBB'), TLA('CCC'), TLA('DDD')],
    start_time=datetime(2014, 4, 26, 16, 30, tzinfo=tzutc()),
    end_time=datetime(2014, 4, 26, 16, 35, tzinfo=tzutc()),
    type=MatchType.knockout,
    use_resolved_ranking=False,
)

TIEBREAKER_INFO = Match(
    num=MatchNumber(2),
    display_name="Tiebreaker (#2)",
    arena=ArenaName('A'),
    teams=[TLA('AAA'), TLA('BBB')],
    start_time=datetime(2014, 4, 26, 16, 30, tzinfo=tzutc()),
    end_time=datetime(2014, 4, 26, 16, 35, tzinfo=tzutc()),
    type=MatchType.tiebreaker,
    use_resolved_ranking=False,
)

TEAMS = {
    TLA('AAA'): Team(tla=TLA('AAA'), name="AAA Squad", rookie=True, dropped_out_after=None),
    TLA('BBB'): Team(tla=TLA('BBB'), name="BBBees", rookie=False, dropped_out_after=None),
    TLA('CCC'): Team(tla=TLA('CCC'), name="Team CCC", rookie=True, dropped_out_after=None),
    TLA('DDD'): Team(tla=TLA('DDD'), name="DDD Robots", rookie=False, dropped_out_after=None),
}


class MockScoreSet:
    def __init__(self, arena, game, scores, dsq=()):
        positions = calc_positions(scores, dsq)
        league_points = calc_ranked_points(positions, dsq)
        team_key = {}
        gp_key = {}
        rp_key = {}
        for team, gp in scores.items():
            lp = league_points[team]
            team_key[team] = TeamScore(league=lp, game=gp)
            gp_key[team] = gp
            rp_key[team] = lp
        self.teams = team_key
        self.game_points = {(arena, game): gp_key}
        self.ranked_points = {(arena, game): rp_key}
        self.game_positions = {(arena, game): positions}
        self.positions = OrderedDict()
        for position, teams in positions.items():
            for team in teams:
                self.positions[team] = position


class MockScores:
    def __init__(
        self,
        league={'AAA': 1, 'BBB': 2, 'CCC': 0, 'DDD': 0},
        league_dsq=(),
        knockout={'AAA': 0, 'BBB': 3, 'CCC': 0, 'DDD': 2},
        knockout_dsq=('CCC',),
    ):
        self.knockout = MockScoreSet('A', 1, knockout, knockout_dsq)
        self.league = MockScoreSet('A', 0, league, league_dsq)


def build_tiebreaker_scores():
    knockout_game_score = {'AAA': 2, 'BBB': 2, 'CCC': 1, 'DDD': 0}
    tiebreaker_game_score = {'AAA': 1, 'BBB': 2}
    scores = MockScores(knockout=knockout_game_score)
    scores.tiebreaker = MockScoreSet('A', 2, tiebreaker_game_score, ())
    return scores


class WinnersTests(unittest.TestCase):
    def test_first_tiebreaker(self):
        scores = build_tiebreaker_scores()
        self.assertEqual(
            ['BBB'],
            compute_awards(scores, TIEBREAKER_INFO, TEAMS).get(Award.first),
        )

    def test_second_tiebreaker(self):
        scores = build_tiebreaker_scores()
        self.assertEqual(
            ['AAA'],
            compute_awards(scores, TIEBREAKER_INFO, TEAMS).get(Award.second),
        )

    def test_third_tiebreaker(self):
        # Needs to look in the scores for the final
        scores = build_tiebreaker_scores()
        self.assertEqual(
            ['DDD'],
            compute_awards(scores, TIEBREAKER_INFO, TEAMS).get(Award.third),
        )

    def test_first(self):
        self.assertEqual(
            ['BBB'],
            compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.first),
        )

    def test_second(self):
        self.assertEqual(
            ['DDD'],
            compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.second),
        )

    def test_third(self):
        self.assertEqual(
            ['AAA'],
            compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.third),
        )

    def test_tied(self):
        awards = compute_awards(
            MockScores(
                knockout={'AAA': 1, 'BBB': 1, 'CCC': 1, 'DDD': 1},
                knockout_dsq=(),
            ),
            FINAL_INFO,
            TEAMS,
        )
        self.assertEqual(
            ['AAA', 'BBB', 'CCC', 'DDD'],
            awards.get(Award.first),
        )

    def test_tied_partial(self):
        awards = compute_awards(
            MockScores(
                knockout={'AAA': 2, 'BBB': 1, 'CCC': 1, 'DDD': 1},
                knockout_dsq=(),
            ), FINAL_INFO, TEAMS,
        )
        self.assertEqual(
            ['AAA'],
            awards.get(Award.first),
        )

    def test_rookie(self):
        self.assertEqual(
            ['AAA'],
            compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.rookie),
        )

    def test_tied_rookie(self):
        scores = MockScores(league={'AAA': 0, 'BBB': 0, 'CCC': 0, 'DDD': 0})
        self.assertEqual(
            ['AAA', 'CCC'],
            compute_awards(scores, FINAL_INFO, TEAMS).get(Award.rookie),
        )

    def test_override(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.return_value = {'third': 'DDD'}
            self.assertEqual(
                ['DDD'],
                compute_awards(MockScores(), FINAL_INFO, TEAMS, Path('.')).get(Award.third),
            )
            yaml_load.assert_called_with(Path('.'))

    def test_manual(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.return_value = {'web': 'BBB'}
            self.assertEqual(
                ['BBB'],
                compute_awards(MockScores(), FINAL_INFO, TEAMS, Path('.')).get(Award.web),
            )
            yaml_load.assert_called_with(Path('.'))

    def test_manual_no_award(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.return_value = {'web': []}
            self.assertEqual(
                [],
                compute_awards(MockScores(), FINAL_INFO, TEAMS, Path('.')).get(Award.web),
            )
            yaml_load.assert_called_with(Path('.'))

    def test_manual_tie(self):
        with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
            yaml_load.return_value = {'web': ['BBB', 'CCC']}
            self.assertEqual(
                ['BBB', 'CCC'],
                compute_awards(MockScores(), FINAL_INFO, TEAMS, Path('.')).get(Award.web),
            )
            yaml_load.assert_called_with(Path('.'))

    def test_no_overrides_file(self):
        self.assertEqual(
            ['AAA'],
            compute_awards(MockScores(), FINAL_INFO, TEAMS, Path('missing.yaml')).get(Award.third),
        )
