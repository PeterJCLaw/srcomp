import datetime
import unittest
from collections import defaultdict
from unittest import mock

from league_ranker import calc_positions, calc_ranked_points
from nose.tools import eq_

from sr.comp.match_period import Match, MatchPeriod, MatchType
from sr.comp.matches import MatchSchedule
from sr.comp.teams import Team


def make_schedule():
    settings = {
        'match_periods': {'league': [], 'knockout': []},
        'match_slot_lengths': {
            'pre': 90,
            'match': 180,
            'post': 30,
            'total': 300,
        },
        'staging': {
            'opens': 300,
            'closes': 120,
            'duration': 180,
            'signal_shepherds': {
                'Blue': 241,
                'Green': 181,
            },
            'signal_teams': 240,
        },
        'league': {'extra_spacing': []},
        'delays': [],
    }
    teams = defaultdict(lambda: Team(None, None, False, None))
    schedule = MatchSchedule(settings, {}, teams, 4)

    finals = Match(
        num=0,
        display_name="Match 0",
        arena='A',
        teams=['AAA', 'BBB', 'CCC', 'DDD'],
        start_time=datetime.datetime(2014, 4, 25, 12, 0),
        end_time=datetime.datetime(2014, 4, 25, 12, 5),
        type=MatchType.knockout,
        use_resolved_ranking=False,
    )
    schedule.knockout_rounds = [[finals]]
    schedule.matches.append({'A': finals})

    return schedule


def make_finals_score(game_points):
    positions = calc_positions(game_points)
    ranked = calc_ranked_points(positions)
    ko_scores = mock.Mock()
    ko_scores.game_points = {('A', 0): game_points}
    ko_scores.game_positions = {('A', 0): positions}
    ko_scores.ranked_points = {('A', 0): ranked}
    scores = mock.Mock()
    scores.knockout = ko_scores
    return scores


class TiebreakerTests(unittest.TestCase):
    def test_tiebreaker(self):
        schedule = make_schedule()
        scores = make_finals_score({
            'AAA': 1,
            'BBB': 1,
            'CCC': 1,
            'DDD': 0,
        })

        schedule.add_tiebreaker(scores, datetime.datetime(2014, 4, 25, 13, 0))

        assert schedule.tiebreaker

        start_time = datetime.datetime(2014, 4, 25, 13, 0)
        end_time = datetime.datetime(2014, 4, 25, 13, 5)

        tiebreaker_match = {
            'A': Match(
                num=1,
                display_name="Tiebreaker (#1)",
                arena='A',
                teams=['BBB', 'AAA', None, 'CCC'],
                start_time=start_time,
                end_time=end_time,
                type=MatchType.tiebreaker,
                use_resolved_ranking=False,
            ),
        }

        eq_(schedule.matches[-1], tiebreaker_match)

        last_period = schedule.match_periods[-1]
        last_period_matches = last_period.matches

        assert last_period_matches == [tiebreaker_match], "Wrong matches in last period"

        last_period_matches.pop()  # simplify the next comparison

        expected_period = MatchPeriod(
            start_time, end_time, end_time,
            'Tiebreaker', [], MatchType.tiebreaker,
        )

        assert last_period == expected_period, "Wrong last period"

    def test_no_tiebreaker_if_winner(self):
        schedule = make_schedule()
        scores = make_finals_score({
            'AAA': 2,
            'BBB': 1,
            'CCC': 1,
            'DDD': 0,
        })

        schedule.add_tiebreaker(scores, datetime.datetime(2014, 4, 25, 13, 0))
        eq_(schedule.n_matches(), 1)

        with self.assertRaises(AttributeError):
            schedule.tiebreaker

    def test_no_tiebreaker_if_no_final(self):
        schedule = make_schedule()
        scores = mock.Mock()
        scores.knockout = mock.Mock()
        scores.knockout.game_points = {}
        scores.knockout.game_positions = {}
        scores.knockout.ranked_points = {}

        schedule.add_tiebreaker(scores, datetime.datetime(2014, 4, 25, 13, 0))
        eq_(schedule.n_matches(), 1)

        with self.assertRaises(AttributeError):
            schedule.tiebreaker

    def test_final_match_no_tiebreaker(self):
        schedule = make_schedule()

        expected = schedule.matches[0]['A']
        final_info = schedule.final_match

        assert expected.display_name == 'Match 0', "Sanity check"
        assert expected == final_info

    def test_final_match_with_tiebreaker(self):
        schedule = make_schedule()
        scores = make_finals_score({
            'AAA': 1,
            'BBB': 1,
            'CCC': 1,
            'DDD': 0,
        })
        schedule.add_tiebreaker(scores, datetime.datetime(2014, 4, 25, 13, 0))

        expected = schedule.matches[1]['A']
        final_info = schedule.final_match

        assert expected.display_name == 'Tiebreaker (#1)', "Sanity check"
        assert expected == final_info
