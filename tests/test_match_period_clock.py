from sr.comp.matches import Delay
from sr.comp.match_period import MatchPeriod
from sr.comp.match_period_clock import MatchPeriodClock, OutOfTimeException


def build_match_period(start, end, max_end=None, desc=None, matches=None, type_=None):
    return MatchPeriod(start, end, max_end or end, desc, matches, type_)


def check_out_of_time(clock, msg=None):
    threw = False
    try:
        curr_time = clock.current_time
        print(curr_time)  # Useful for debugging, also prevents 'unused variable' warnings
    except OutOfTimeException:
        threw = True

    msg = msg or "Should signal that we're beyond the end of the period" \
                 " by raising a '{}'".format(OutOfTimeException)

    assert threw, msg


# Test current_time at start


def test_current_time_start():
    period = build_match_period(0, 4)
    clock = MatchPeriodClock(period, [])

    curr_time = clock.current_time

    assert 0 == curr_time, "Should start at the start of the period"


def test_current_time_start_delayed():
    period = build_match_period(0, 4)
    clock = MatchPeriodClock(period, [Delay(time=0, delay=1)])

    curr_time = clock.current_time

    assert 1 == curr_time, "Start time should include delays"


def test_current_time_start_delayed_twice():
    period = build_match_period(0, 10)
    delays = [
        Delay(time=0, delay=2),
        Delay(time=1, delay=3),
    ]
    clock = MatchPeriodClock(period, delays)

    curr_time = clock.current_time

    assert 5 == curr_time, "Start time should include cumilative delays"


# Test current_time at end


def test_current_time_at_end_no_delay():
    period = build_match_period(0, 1)
    clock = MatchPeriodClock(period, [])

    clock.advance_time(1)

    curr_time = clock.current_time
    assert 1 == curr_time, "Should be able to query time when at end"


def test_current_time_at_max_end_no_delay():
    period = build_match_period(0, 1, 2)
    clock = MatchPeriodClock(period, [])

    clock.advance_time(2)

    check_out_of_time(
        clock,
        "Should be out of time when at max_end due to over-advancing",
    )


def test_current_time_at_max_end_with_delay():
    period = build_match_period(0, 1, 2)
    clock = MatchPeriodClock(period, [Delay(time=1, delay=1)])

    clock.advance_time(1)

    curr_time = clock.current_time
    assert 2 == curr_time, "Should be able to query time when at max_end" \
                           " due to delays"


# Test current_time beyond end


def test_current_time_beyond_end_no_delay():
    period = build_match_period(0, 1)
    clock = MatchPeriodClock(period, [])

    clock.advance_time(5)
    check_out_of_time(clock)


def test_current_time_beyond_end_with_delay():
    period = build_match_period(0, 1)
    clock = MatchPeriodClock(period, [Delay(time=1, delay=1)])

    clock.advance_time(1)
    # now at 2
    check_out_of_time(clock)


def test_current_time_beyond_max_end_no_delay():
    period = build_match_period(0, 1, 2)
    clock = MatchPeriodClock(period, [])

    clock.advance_time(5)
    check_out_of_time(clock)


def test_current_time_beyond_max_end_with_delay():
    period = build_match_period(0, 1, 2)
    clock = MatchPeriodClock(period, [Delay(time=1, delay=2)])

    clock.advance_time(1)
    # now at 3
    check_out_of_time(clock)


# Test advance_time


def test_advance_time_no_delays():
    period = build_match_period(0, 10)
    clock = MatchPeriodClock(period, [])
    curr_time = clock.current_time
    assert 0 == curr_time, "Should start at the start of the period"

    clock.advance_time(1)

    curr_time = clock.current_time
    assert 1 == curr_time, "Time should advance by the given amount (1)"

    clock.advance_time(2)

    curr_time = clock.current_time
    assert 3 == curr_time, "Time should advance by the given amount (2)"


def test_advance_time_with_delays():
    period = build_match_period(0, 50)
    delays = [
        Delay(time=1, delay=1),
        Delay(time=5, delay=2),
    ]
    clock = MatchPeriodClock(period, delays)
    curr_time = clock.current_time
    assert 0 == curr_time, "Should start at the start of the period"

    clock.advance_time(1)  # plus a delay of 2 at time=1

    curr_time = clock.current_time
    assert 2 == curr_time, "Time should advance by the given amount (1)" \
                           " plus the size of the delay it meets"

    clock.advance_time(2)

    curr_time = clock.current_time
    assert 4 == curr_time, "Time should advance by the given amount (2)" \
                           " only; there are no intervening delays"

    clock.advance_time(2)  # takes us to 6, plus a delay of 2 at time=5

    curr_time = clock.current_time
    assert 8 == curr_time, "Time should advance by the given amount (2)" \
                           " plus the size of the intervening delay (2)"

    clock.advance_time(2)

    curr_time = clock.current_time
    assert 10 == curr_time, "Time should advance by the given amount (2)" \
                            " only; there are no intervening delays"


def test_advance_time_overlapping_delays():
    period = build_match_period(0, 10)
    delays = [
        Delay(time=1, delay=2),  # from 1 -> 3
        Delay(time=2, delay=1),  # extra at 2, so 1 -> 4
    ]
    clock = MatchPeriodClock(period, delays)
    curr_time = clock.current_time
    assert 0 == curr_time, "Should start at the start of the period"

    clock.advance_time(2)  # plus a total delay of 3

    curr_time = clock.current_time
    assert 5 == curr_time, "Time should advance by the given amount (2)" \
                           " plus the size of the intervening delays (1+2)"


def test_advance_time_touching_delays():
    period = build_match_period(0, 10)
    delays = [
        Delay(time=1, delay=1),  # from 1 -> 2
        Delay(time=2, delay=1),  # from 2 -> 3
    ]
    clock = MatchPeriodClock(period, delays)
    curr_time = clock.current_time
    assert 0 == curr_time, "Should start at the start of the period"

    clock.advance_time(2)  # plus a total delay of 2

    curr_time = clock.current_time
    assert 4 == curr_time, "Time should advance by the given amount (2)" \
                           " plus the size of the intervening delays (1+1)"


# Test slots


def test_slots_no_delays_1():
    period = build_match_period(0, 4)
    clock = MatchPeriodClock(period, [])
    slots = list(clock.iterslots(1))
    expected = list(range(5))
    assert expected == slots


def test_slots_no_delays_2():
    period = build_match_period(0, 4)
    clock = MatchPeriodClock(period, [])
    slots = list(clock.iterslots(2))
    expected = [0, 2, 4]
    assert expected == slots


def test_slots_delay_before():
    period = build_match_period(0, 4)
    clock = MatchPeriodClock(period, [Delay(time=-1, delay=2)])

    curr_time = clock.current_time
    assert 0 == curr_time, "Should start at the start of the period"

    slots = list(clock.iterslots(1))
    expected = list(range(5))
    assert expected == slots


def test_slots_delay_after():
    period = build_match_period(0, 4)
    clock = MatchPeriodClock(period, [Delay(time=6, delay=2)])

    curr_time = clock.current_time
    assert 0 == curr_time, "Should start at the start of the period"

    slots = list(clock.iterslots(1))
    expected = list(range(5))
    assert expected == slots


def test_slots_delay_during():
    period = build_match_period(0, 4, 5)
    clock = MatchPeriodClock(period, [Delay(time=1, delay=3)])
    slots = list(clock.iterslots(2))
    expected = [0, 5]
    assert expected == slots


def test_slots_extra_gap():
    period = build_match_period(0, 6)
    clock = MatchPeriodClock(period, [])
    slots = []
    first_time = True
    for start in clock.iterslots(2):
        slots.append(clock.current_time)
        if first_time:
            # Advance an extra 3 the first time
            clock.advance_time(3)
            # Now at 5
            first_time = False
    expected = [0, 5]
    assert expected == slots
