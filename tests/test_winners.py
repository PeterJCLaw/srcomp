from datetime import datetime
from dateutil.tz import tzutc
from collections import OrderedDict

from sr.comp.winners import Award, compute_awards
from sr.comp.match_period import Match, MatchType
from sr.comp.teams import Team
from sr.comp.scores import TeamScore
from sr.comp.ranker import calc_positions, calc_ranked_points

from nose.tools import eq_
import mock


FINAL_INFO = Match(
    num=1,
    display_name="Match 1",
    arena='A',
    teams=['AAA', 'BBB', 'CCC', 'DDD'],
    start_time=datetime(2014, 4, 26, 16, 30, tzinfo=tzutc()),
    end_time=datetime(2014, 4, 26, 16, 35, tzinfo=tzutc()),
    type=MatchType.knockout,
    use_resolved_ranking=False,
)

TIEBREAKER_INFO = Match(
    num=2,
    display_name="Tiebreaker (#2)",
    arena='A',
    teams=['AAA', 'BBB'],
    start_time=datetime(2014, 4, 26, 16, 30, tzinfo=tzutc()),
    end_time=datetime(2014, 4, 26, 16, 35, tzinfo=tzutc()),
    type=MatchType.tiebreaker,
    use_resolved_ranking=False,
)

TEAMS = {
    'AAA': Team(tla='AAA', name="AAA Squad", rookie=True, dropped_out_after=None),
    'BBB': Team(tla='BBB', name="BBBees", rookie=False, dropped_out_after=None),
    'CCC': Team(tla='CCC', name="Team CCC", rookie=True, dropped_out_after=None),
    'DDD': Team(tla='DDD', name="DDD Robotics", rookie=False, dropped_out_after=None),
}


class MockScoreSet(object):
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


class MockScores(object):
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


def test_first_tiebreaker():
    scores = build_tiebreaker_scores()
    eq_(compute_awards(scores, TIEBREAKER_INFO, TEAMS).get(Award.first), ['BBB'])


def test_second_tiebreaker():
    scores = build_tiebreaker_scores()
    eq_(compute_awards(scores, TIEBREAKER_INFO, TEAMS).get(Award.second), ['AAA'])


def test_third_tiebreaker():
    # Needs to look in the scores for the final
    scores = build_tiebreaker_scores()
    eq_(compute_awards(scores, TIEBREAKER_INFO, TEAMS).get(Award.third), ['DDD'])


def test_first():
    eq_(
        compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.first),
        ['BBB'],
    )


def test_second():
    eq_(
        compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.second),
        ['DDD'],
    )


def test_third():
    eq_(
        compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.third),
        ['AAA'],
    )


def test_tied():
    eq_(
        compute_awards(
            MockScores(
                knockout={'AAA': 1, 'BBB': 1, 'CCC': 1, 'DDD': 1},
                knockout_dsq=(),
            ),
            FINAL_INFO,
            TEAMS,
        ).get(Award.first),
        ['AAA', 'BBB', 'CCC', 'DDD'],
    )


def test_tied_partial():
    eq_(
        compute_awards(
            MockScores(
                knockout={'AAA': 2, 'BBB': 1, 'CCC': 1, 'DDD': 1},
                knockout_dsq=(),
            ), FINAL_INFO, TEAMS,
        ).get(Award.first),
        ['AAA'],
    )


def test_rookie():
    eq_(
        compute_awards(MockScores(), FINAL_INFO, TEAMS).get(Award.rookie),
        ['AAA'],
    )


def test_tied_rookie():
    scores = MockScores(league={'AAA': 0, 'BBB': 0, 'CCC': 0, 'DDD': 0})
    eq_(
        compute_awards(scores, FINAL_INFO, TEAMS).get(Award.rookie),
        ['AAA', 'CCC'],
    )


def test_override():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.return_value = {'third': 'DDD'}
        eq_(
            compute_awards(MockScores(), FINAL_INFO, TEAMS, '.').get(Award.third),
            ['DDD'],
        )
        yaml_load.assert_called_with('.')


def test_manual():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.return_value = {'web': 'BBB'}
        eq_(
            compute_awards(MockScores(), FINAL_INFO, TEAMS, '.').get(Award.web),
            ['BBB'],
        )
        yaml_load.assert_called_with('.')


def test_manual_no_award():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.return_value = {'web': []}
        eq_(
            compute_awards(MockScores(), FINAL_INFO, TEAMS, '.').get(Award.web),
            [],
        )
        yaml_load.assert_called_with('.')


def test_manual_tie():
    with mock.patch('sr.comp.yaml_loader.load') as yaml_load:
        yaml_load.return_value = {'web': ['BBB', 'CCC']}
        eq_(
            compute_awards(MockScores(), FINAL_INFO, TEAMS, '.').get(Award.web),
            ['BBB', 'CCC'],
        )
        yaml_load.assert_called_with('.')


def test_no_overrides_file():
    with mock.patch('os.path.exists') as test_file:
        test_file.return_value = False
        eq_(
            compute_awards(MockScores(), FINAL_INFO, TEAMS, '.').get(Award.third),
            ['AAA'],
        )
