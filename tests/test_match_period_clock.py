import datetime
import unittest
from typing import List, Optional

from sr.comp.match_period import MatchPeriod, MatchSlot, MatchType
from sr.comp.match_period_clock import MatchPeriodClock, OutOfTimeException
from sr.comp.matches import Delay


class MatchPeriodClockTestsBase(unittest.TestCase):
    def build_match_period(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
        max_end: Optional[datetime.datetime] = None,
        desc: str = '',
        matches: Optional[List[MatchSlot]] = None,
        type_: MatchType = MatchType.league,
    ) -> MatchPeriod:
        return MatchPeriod(start, end, max_end or end, desc, matches or [], type_)

    def assertOutOfTime(
        self,
        clock,
        msg="Should signal that we're beyond the end of the period",
    ):
        with self.assertRaises(OutOfTimeException, msg=msg):
            curr_time = clock.current_time
            print(curr_time)  # Useful for debugging, also prevents 'unused variable' warnings


class CurrentTimeTests(MatchPeriodClockTestsBase):
    # At start

    def test_at_start(self):
        period = self.build_match_period(0, 4)
        clock = MatchPeriodClock(period, [])

        curr_time = clock.current_time

        self.assertEqual(0, curr_time, "Should start at the start of the period")

    def test_at_start_delayed(self):
        period = self.build_match_period(0, 4)
        clock = MatchPeriodClock(period, [Delay(time=0, delay=1)])

        curr_time = clock.current_time

        self.assertEqual(1, curr_time, "Start time should include delays")

    def test_at_start_delayed_twice(self):
        period = self.build_match_period(0, 10)
        delays = [
            Delay(time=0, delay=2),
            Delay(time=1, delay=3),
        ]
        clock = MatchPeriodClock(period, delays)

        curr_time = clock.current_time

        self.assertEqual(5, curr_time, "Start time should include cumilative delays")

    # At end

    def test_at_end_no_delay(self):
        period = self.build_match_period(0, 1)
        clock = MatchPeriodClock(period, [])

        clock.advance_time(1)

        curr_time = clock.current_time
        self.assertEqual(1, curr_time, "Should be able to query time when at end")

    def test_at_max_end_no_delay(self):
        period = self.build_match_period(0, 1, 2)
        clock = MatchPeriodClock(period, [])

        clock.advance_time(2)

        self.assertOutOfTime(
            clock,
            "Should be out of time when at max_end due to over-advancing",
        )

    def test_at_max_end_with_delay(self):
        period = self.build_match_period(0, 1, 2)
        clock = MatchPeriodClock(period, [Delay(time=1, delay=1)])

        clock.advance_time(1)

        curr_time = clock.current_time
        self.assertEqual(
            2,
            curr_time,
            "Should be able to query time when at max_end due to delays",
        )

    # Beyond end

    def test_beyond_end_no_delay(self):
        period = self.build_match_period(0, 1)
        clock = MatchPeriodClock(period, [])

        clock.advance_time(5)
        self.assertOutOfTime(clock)

    def test_beyond_end_with_delay(self):
        period = self.build_match_period(0, 1)
        clock = MatchPeriodClock(period, [Delay(time=1, delay=1)])

        clock.advance_time(1)
        # now at 2
        self.assertOutOfTime(clock)

    def test_beyond_max_end_no_delay(self):
        period = self.build_match_period(0, 1, 2)
        clock = MatchPeriodClock(period, [])

        clock.advance_time(5)
        self.assertOutOfTime(clock)

    def test_beyond_max_end_with_delay(self):
        period = self.build_match_period(0, 1, 2)
        clock = MatchPeriodClock(period, [Delay(time=1, delay=2)])

        clock.advance_time(1)
        # now at 3
        self.assertOutOfTime(clock)


class AdvanceTimeTests(MatchPeriodClockTestsBase):
    def test_no_delays(self):
        period = self.build_match_period(0, 10)
        clock = MatchPeriodClock(period, [])
        curr_time = clock.current_time
        self.assertEqual(0, curr_time, "Should start at the start of the period")

        clock.advance_time(1)

        curr_time = clock.current_time
        self.assertEqual(1, curr_time, "Time should advance by the given amount (1)")

        clock.advance_time(2)

        curr_time = clock.current_time
        self.assertEqual(3, curr_time, "Time should advance by the given amount (2)")

    def test_with_delays(self):
        period = self.build_match_period(0, 50)
        delays = [
            Delay(time=1, delay=1),
            Delay(time=5, delay=2),
        ]
        clock = MatchPeriodClock(period, delays)
        curr_time = clock.current_time
        self.assertEqual(0, curr_time, "Should start at the start of the period")

        clock.advance_time(1)  # plus a delay of 2 at time=1

        curr_time = clock.current_time
        self.assertEqual(
            2,
            curr_time,
            "Time should advance by the given amount (1) plus the size of the "
            "delay it meets",
        )

        clock.advance_time(2)

        curr_time = clock.current_time
        self.assertEqual(
            4,
            curr_time,
            "Time should advance by the given amount (2) only; there are no "
            "intervening delays",
        )

        clock.advance_time(2)  # takes us to 6, plus a delay of 2 at time=5

        curr_time = clock.current_time
        self.assertEqual(
            8,
            curr_time,
            "Time should advance by the given amount (2) plus the size of the "
            "intervening delay (2)",
        )

        clock.advance_time(2)

        curr_time = clock.current_time
        self.assertEqual(
            10,
            curr_time,
            "Time should advance by the given amount (2) only; there are no "
            "intervening delays",
        )

    def test_overlapping_delays(self):
        period = self.build_match_period(0, 10)
        delays = [
            Delay(time=1, delay=2),  # from 1 -> 3
            Delay(time=2, delay=1),  # extra at 2, so 1 -> 4
        ]
        clock = MatchPeriodClock(period, delays)
        curr_time = clock.current_time
        self.assertEqual(0, curr_time, "Should start at the start of the period")

        clock.advance_time(2)  # plus a total delay of 3

        curr_time = clock.current_time
        self.assertEqual(
            5,
            curr_time,
            "Time should advance by the given amount (2) plus the size of the "
            "intervening delays (1+2)",
        )

    def test_touching_delays(self):
        period = self.build_match_period(0, 10)
        delays = [
            Delay(time=1, delay=1),  # from 1 -> 2
            Delay(time=2, delay=1),  # from 2 -> 3
        ]
        clock = MatchPeriodClock(period, delays)
        curr_time = clock.current_time
        self.assertEqual(0, curr_time, "Should start at the start of the period")

        clock.advance_time(2)  # plus a total delay of 2

        curr_time = clock.current_time
        self.assertEqual(
            4,
            curr_time,
            "Time should advance by the given amount (2) plus the size of the "
            "intervening delays (1+1)",
        )


class SlotsTests(MatchPeriodClockTestsBase):
    def test_no_delays_1(self):
        period = self.build_match_period(0, 4)
        clock = MatchPeriodClock(period, [])
        slots = list(clock.iterslots(1))
        expected = list(range(5))
        self.assertEqual(expected, slots)

    def test_no_delays_2(self):
        period = self.build_match_period(0, 4)
        clock = MatchPeriodClock(period, [])
        slots = list(clock.iterslots(2))
        expected = [0, 2, 4]
        self.assertEqual(expected, slots)

    def test_delay_before(self):
        period = self.build_match_period(0, 4)
        clock = MatchPeriodClock(period, [Delay(time=-1, delay=2)])

        curr_time = clock.current_time
        self.assertEqual(0, curr_time, "Should start at the start of the period")

        slots = list(clock.iterslots(1))
        expected = list(range(5))
        self.assertEqual(expected, slots)

    def test_delay_after(self):
        period = self.build_match_period(0, 4)
        clock = MatchPeriodClock(period, [Delay(time=6, delay=2)])

        curr_time = clock.current_time
        self.assertEqual(0, curr_time, "Should start at the start of the period")

        slots = list(clock.iterslots(1))
        expected = list(range(5))
        self.assertEqual(expected, slots)

    def test_delay_during(self):
        period = self.build_match_period(0, 4, 5)
        clock = MatchPeriodClock(period, [Delay(time=1, delay=3)])
        slots = list(clock.iterslots(2))
        expected = [0, 5]
        self.assertEqual(expected, slots)

    def test_extra_gap(self):
        period = self.build_match_period(0, 6)
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
        self.assertEqual(expected, slots)
