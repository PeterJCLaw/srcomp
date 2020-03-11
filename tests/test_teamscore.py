from sr.comp.scores import TeamScore


def test_empty_ctor():
    ts = TeamScore()
    assert ts.game_points == 0
    assert ts.league_points == 0


def test_ctor_args():
    ts = TeamScore(game=5, league=4.2)
    assert ts.game_points == 5
    assert ts.league_points == 4.2


def test_not_equal_none():
    ts = TeamScore(game=5, league=4.2)
    assert not ts == None  # noqa:E711  # intentional None equality check
    assert ts != None  # noqa:E711  # intentional None equality check


def test_not_equal_empty():
    ts1 = TeamScore()
    ts2 = TeamScore(game=5, league=4.2)
    assert ts1 != ts2
    assert ts2 != ts1
    assert not ts1 == ts2
    assert not ts2 == ts1


def test_equal_self_empty():
    ts = TeamScore()
    assert ts == ts
    assert not ts != ts


def test_equal_self():
    ts = TeamScore(game=5, league=4.5)
    assert ts == ts
    assert not ts != ts


def test_equal_other_same_values():
    ts1 = TeamScore(game=5, league=4.5)
    ts2 = TeamScore(game=5, league=4.5)
    assert ts1 == ts2
    assert ts2 == ts1
    assert not ts1 != ts2
    assert not ts2 != ts1


def test_not_equal_other_similar_values():
    ts1 = TeamScore(game=5, league=4)
    ts2 = TeamScore(game=5, league=4.5)
    assert ts1 != ts2
    assert ts2 != ts1
    assert not ts1 == ts2
    assert not ts2 == ts1


# Scores with more points are greater than those with fewer


def assert_rich_comparisons(smaller, larger):
    assert smaller < larger
    assert smaller <= larger
    assert larger > smaller
    assert larger >= smaller
    assert not smaller > larger
    assert not smaller >= larger
    assert not larger < smaller
    assert not larger <= smaller


def test_rich_comparisons_helper():
    assert_rich_comparisons(1, 2)


def test_rich_comparisons_helper_fail():
    try:
        assert_rich_comparisons(2, 1)
    except:
        pass
    else:
        assert False, "Should have found 1 < 2"


def test_rich_comparisons_none():
    ts = TeamScore(game=5, league=4)
    assert_rich_comparisons(None, ts)


def test_rich_comparisons_empty():
    ts = TeamScore(game=5, league=4)
    empty = TeamScore()
    assert_rich_comparisons(empty, ts)


def test_rich_comparisons_self():
    ts = TeamScore(game=5, league=4)
    assert ts >= ts
    assert ts <= ts
    assert not ts > ts
    assert not ts < ts


def test_rich_comparisons_same_values():
    ts1 = TeamScore(game=5, league=4)
    ts2 = TeamScore(game=5, league=4)
    assert ts1 >= ts2
    assert ts1 <= ts2
    assert not ts1 > ts2
    assert not ts1 < ts2


def test_rich_comparisons_same_game():
    ts1 = TeamScore(game=5, league=4)
    ts2 = TeamScore(game=5, league=4.5)
    assert_rich_comparisons(ts1, ts2)


def test_rich_comparisons_same_league():
    ts2 = TeamScore(game=15, league=4)
    ts1 = TeamScore(game=5, league=4)
    # Tied on league points, but game points differentiate
    assert_rich_comparisons(ts1, ts2)


def test_rich_comparisons_both_differ():
    ts2 = TeamScore(game=5, league=10)
    ts1 = TeamScore(game=25, league=4)
    # Only care about league points really -- game are tie-break only
    assert_rich_comparisons(ts1, ts2)
