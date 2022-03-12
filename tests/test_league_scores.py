import unittest
from typing import Iterable, List

from sr.comp.scores import LeagueScores, TeamScore
from sr.comp.types import ScoreData, TLA

from .factories import build_score_data, FakeScorer


def load_data(the_data: ScoreData) -> LeagueScores:
    teams = the_data['teams'].keys()
    return load_datas([the_data], teams)


def load_datas(the_datas: List[ScoreData], teams: Iterable[TLA]) -> LeagueScores:
    scores = LeagueScores(
        the_datas,
        teams,
        FakeScorer,
        num_teams_per_arena=4,
    )
    return scores


def get_score_data(
    num: int = 123,
    arena: str = 'A',
) -> ScoreData:
    data = build_score_data(num, arena)
    data['teams'][TLA('JMS')]['disqualified'] = True
    data['teams'][TLA('PAS')]['present'] = False
    return data


def load_basic_data() -> LeagueScores:
    return load_data(get_score_data())


class LeagueScoresTests(unittest.TestCase):
    def test_game_points(self):
        scores = load_basic_data()

        games = scores.game_points
        self.assertEqual(1, len(games))

        id_ = ('A', 123)
        self.assertIn(id_, games)

        game = games[id_]

        self.assertEqual({'JMS': 4, 'PAS': 0, 'RUN': 8, 'ICE': 2}, game)

    def test_league_points(self):
        scores = load_basic_data()

        leagues = scores.ranked_points
        self.assertEqual(1, len(leagues))

        id_ = ('A', 123)
        self.assertIn(id_, leagues)

        league = leagues[id_]

        self.assertEqual({'JMS': 0, 'PAS': 0, 'RUN': 8, 'ICE': 6}, league)

    def test_team_points(self):
        scores = load_basic_data()

        expected = {
            'JMS': TeamScore(0, 4),
            'PAS': TeamScore(0, 0),
            'RUN': TeamScore(8, 8),
            'ICE': TeamScore(6, 2),
        }

        self.assertEqual(expected, scores.teams)

    def test_last_scored_match(self):
        m_1 = get_score_data(num=1)
        scores = load_data(m_1)

        self.assertEqual(
            1,
            scores.last_scored_match,
            "Should match id of only match present.",
        )

    def test_last_scored_match_none(self):
        scores = load_datas([], [])

        self.assertIsNone(
            scores.last_scored_match,
            "Should be none when there are no scores.",
        )

    def test_last_scored_match_some_missing(self):
        scores = load_basic_data()

        self.assertEqual(
            123,
            scores.last_scored_match,
            "Should match id of only match present.",
        )

    def test_last_scored_match_many_scores(self):
        m_1 = get_score_data(num=1)
        m_2B = get_score_data(num=2, arena='B')

        scores = load_datas([m_1, m_2B], m_1['teams'].keys())

        self.assertEqual(
            2,
            scores.last_scored_match,
            "Should latest match id, even when in other arena.",
        )

    def test_league_ranker_simple(self):
        team_scores = {'ABC': TeamScore(), 'DEF': TeamScore(4, 5)}
        ranking = LeagueScores.rank_league(team_scores)
        expected_map = {
            'DEF': 1,
            'ABC': 2,
        }
        expected_order = ['DEF', 'ABC']

        self.assertEqual(expected_map, ranking)
        order = list(ranking.keys())
        self.assertEqual(expected_order, order)

    def test_league_ranker_league_tie(self):
        team_scores = {
            'ABC': TeamScore(4, 0),
            'DEF': TeamScore(4, 5),
            'GHI': TeamScore(),
        }
        ranking = LeagueScores.rank_league(team_scores)
        expected_map = {
            'DEF': 1,
            'ABC': 2,
            'GHI': 3,
        }
        expected_order = ['DEF', 'ABC', 'GHI']

        self.assertEqual(expected_map, ranking)
        order = list(ranking.keys())
        self.assertEqual(expected_order, order)

    def test_league_ranker_game_tie(self):
        team_scores = {
            'ABC': TeamScore(0, 5),
            'DEF': TeamScore(4, 5),
            'GHI': TeamScore(),
        }
        ranking = LeagueScores.rank_league(team_scores)
        expected_map = {
            'DEF': 1,
            'ABC': 2,
            'GHI': 3,
        }
        expected_order = ['DEF', 'ABC', 'GHI']

        self.assertEqual(expected_map, ranking)
        order = list(ranking.keys())
        self.assertEqual(expected_order, order)

    # TODO: how do we resolve full ties?
    # TODO: build something to alert us that we have a full tie.

    def test_league_ranker_full_tie(self):
        team_scores = {
            'ABC': TeamScore(4, 5),
            'DEF': TeamScore(4, 5),
            'GHI': TeamScore(),
        }
        ranking = LeagueScores.rank_league(team_scores)
        expected_map = {
            'DEF': 1,
            'ABC': 1,
            'GHI': 3,
        }
        expected_order = ['DEF', 'ABC', 'GHI']

        self.assertEqual(expected_map, ranking)
        order = list(ranking.keys())
        self.assertEqual(expected_order, order)
