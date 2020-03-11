from unittest import mock

from sr.comp.scores import Scores


def test_last_scored_match_none():
    def check(league_lsm, knockout_lsm, tiebreaker_lsm, expected):
        with mock.patch(
            'sr.comp.scores.LeagueScores',
        ) as ls, mock.patch(
            'sr.comp.scores.KnockoutScores',
        ) as ks, mock.patch(
            'sr.comp.scores.TiebreakerScores',
        ) as ts:
            ls.return_value = mock.Mock(last_scored_match=league_lsm)
            ks.return_value = mock.Mock(last_scored_match=knockout_lsm)
            ts.return_value = mock.Mock(last_scored_match=tiebreaker_lsm)

            scores = Scores('', None, None, 0)

            lsm = scores.last_scored_match
            assert expected == lsm

    # No scores yet
    yield check, None, None, None, None

    # League only
    yield check, 13, None, None, 13

    # Knockout only (not actually vaild)
    yield check, None, 42, None, 42

    # Tiebreaker only (not actually vaild)
    yield check, None, None, 42, 42

    # League and Knockout only
    yield check, 13, 42, None, 42

    # All present -- always choose tiebreaker value
    yield check, 13, 37, 42, 42
    yield check, 42, 37, 13, 13
