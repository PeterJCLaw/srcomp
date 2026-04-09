from __future__ import annotations

import datetime
import unittest

from sr.comp.match_period import MatchPeriod, MatchSlot, MatchType
from sr.comp.match_period_clock import (
    MatchPeriodClock,
    OutOfTimeException,
    Spacing,
)
from sr.comp.matches import Delay


class MatchPeriodClockTestsBase(unittest.TestCase):
    def build_match_period(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
        max_end: datetime.datetime | None = None,
        desc: str = '',
        matches: list[MatchSlot] | None = None,
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


class ApplySpacingTests(MatchPeriodClockTestsBase):
    REF = datetime.datetime(2000, 1, 1)

    maxDiff = None

    @classmethod
    def build_delay(cls, *, time: int, delay: int) -> Delay:
        return Delay(
            time=cls.REF.replace(second=time),
            delay=datetime.timedelta(seconds=delay),
        )

    def build_match_period(  # type: ignore[override]
        self,
        start: int,
        end: int,
    ) -> MatchPeriod:
        return super().build_match_period(
            start=self.REF.replace(second=start),
            end=self.REF.replace(second=end),
        )

    def assertApplySpacing(
        self,
        clock: MatchPeriodClock,
        nominal: int,
        flex: int = 0,
        expected_recovery: int | None = None,
    ) -> None:
        recovered = None

        def recovery(delay: Delay) -> None:
            nonlocal recovered
            self.assertIsNone(recovered, "Should only recover time once")
            recovered = -delay.delay.total_seconds()

        clock.apply_spacing(
            Spacing(
                delay_flex=datetime.timedelta(seconds=flex),
                minimum=datetime.timedelta(seconds=nominal - flex),
                nominal=datetime.timedelta(seconds=nominal),
            ),
            recover_time=recovery,
        )

        self.assertEqual(expected_recovery, recovered, "Wrong amount of recovered time")

    def assertCurrentTime(self, clock: MatchPeriodClock, seconds: int, message: str) -> None:
        self.assertEqual(
            seconds,
            clock.current_time.second,
            message,
        )

    # No flex -- should behave just like `advance_time`

    def test_no_delays(self) -> None:
        period = self.build_match_period(0, 10)
        clock = MatchPeriodClock(period, [])
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        self.assertApplySpacing(clock, 1)

        self.assertCurrentTime(clock, 1, "Time should advance by the given amount (1)")

        self.assertApplySpacing(clock, 2)

        self.assertCurrentTime(clock, 3, "Time should advance by the given amount (2)")

    def test_with_delays(self) -> None:
        period = self.build_match_period(0, 50)
        delays = [
            self.build_delay(time=1, delay=1),
            self.build_delay(time=5, delay=2),
        ]
        clock = MatchPeriodClock(period, delays)
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        self.assertApplySpacing(clock, 1)  # plus a delay of 1 at time=1

        self.assertCurrentTime(
            clock,
            2,
            "Time should advance by the given amount (1) plus the size of the "
            "delay it meets",
        )

        self.assertApplySpacing(clock, 2)

        self.assertCurrentTime(
            clock,
            4,
            "Time should advance by the given amount (2) only; there are no "
            "intervening delays",
        )

        self.assertApplySpacing(clock, 2)  # takes us to 6, plus a delay of 2 at time=5

        self.assertCurrentTime(
            clock,
            8,
            "Time should advance by the given amount (2) plus the size of the "
            "intervening delay (2)",
        )

        self.assertApplySpacing(clock, 2)

        self.assertCurrentTime(
            clock,
            10,
            "Time should advance by the given amount (2) only; there are no "
            "intervening delays",
        )

    def test_overlapping_delays(self) -> None:
        period = self.build_match_period(0, 10)
        delays = [
            self.build_delay(time=1, delay=2),  # from 1 -> 3
            self.build_delay(time=2, delay=1),  # extra at 2, so 1 -> 4
        ]
        clock = MatchPeriodClock(period, delays)
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        self.assertApplySpacing(clock, 2)  # plus a total delay of 3

        self.assertCurrentTime(
            clock,
            5,
            "Time should advance by the given amount (2) plus the size of the "
            "intervening delays (1+2)",
        )

    def test_touching_delays(self) -> None:
        period = self.build_match_period(0, 10)
        delays = [
            self.build_delay(time=1, delay=1),  # from 1 -> 2
            self.build_delay(time=2, delay=1),  # from 2 -> 3
        ]
        clock = MatchPeriodClock(period, delays)
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        self.assertApplySpacing(clock, 2)  # plus a total delay of 2

        self.assertCurrentTime(
            clock,
            4,
            "Time should advance by the given amount (2) plus the size of the "
            "intervening delays (1+1)",
        )

    # Flex greater than the delays -- should fully absorb the delays

    def test_flex_no_delays(self) -> None:
        period = self.build_match_period(0, 10)
        clock = MatchPeriodClock(period, [])
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        self.assertApplySpacing(clock, 2, flex=1)

        self.assertCurrentTime(clock, 2, "Time should advance by the given amount (2)")

        self.assertApplySpacing(clock, 2, flex=1)

        self.assertCurrentTime(clock, 4, "Time should advance by the given amount (2)")

    def test_flex_ignores_future_delays(self) -> None:
        period = self.build_match_period(0, 50)
        delays = [
            self.build_delay(time=1, delay=1),  # at 1 -> 2
            self.build_delay(time=3, delay=2),  # at 3 -> 5
        ]
        clock = MatchPeriodClock(period, delays)
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        # Flex ignore delays which happen after the start of the spacing we're adding.
        self.assertApplySpacing(clock, 3, flex=2)

        self.assertCurrentTime(
            clock,
            6,
            "Time should advance by the given amount (3) plus the size of the "
            "(future) delays it meets",
        )

    def test_flex_gt_delays_with_delays(self) -> None:
        period = self.build_match_period(0, 50)
        delays = [
            self.build_delay(time=0, delay=1),  # seen, absorbed
            self.build_delay(time=1, delay=1),   # seen, absorbed
            self.build_delay(time=9, delay=2),   # future, ignored initially
        ]
        clock = MatchPeriodClock(period, delays)
        clock.advance_time(datetime.timedelta(seconds=3))   # plus delays (2)
        self.assertCurrentTime(clock, 5, "Should be after the initial delays")

        # Absorbs both delays which were already "expended", but not the one
        # which is in the future.
        self.assertApplySpacing(clock, 5, flex=3, expected_recovery=2)

        self.assertCurrentTime(
            clock,
            8,
            "Time should advance by the given amount (5) minus the historic delays (2)",
        )

        # Doesn't absorb any of the delay which happens "during" this spacing
        self.assertApplySpacing(clock, 2, flex=1, expected_recovery=None)

        self.assertCurrentTime(
            clock,
            12,
            "Time should advance by the given amount (2) plus the size of the "
            "delay it meets (2)",
        )

        # Recovers from the previous delay (2), with some space left over
        self.assertApplySpacing(clock, 4, flex=3, expected_recovery=2)

        self.assertCurrentTime(
            clock,
            14,
            "Time should advance by the given amount (4) minus the historic delays (2)",
        )

        # no flex needed, we're on track
        self.assertApplySpacing(clock, 2, flex=1, expected_recovery=None)

        self.assertCurrentTime(
            clock,
            16,
            "Time should advance by the given amount (2) only; there are no "
            "remaining delays",
        )

    def test_flex_delays_overlapping_delays(self) -> None:
        period = self.build_match_period(0, 10)
        delays = [
            self.build_delay(time=1, delay=2),  # from 1 -> 3
            self.build_delay(time=2, delay=1),  # extra at 2, so 1 -> 4
        ]
        clock = MatchPeriodClock(period, delays)
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        # No flexing, delays are after the spacing starts
        self.assertApplySpacing(clock, 4, flex=3, expected_recovery=None)

        self.assertCurrentTime(
            clock,
            7,
            "Time should advance by the given amount (4) absorbing the "
            "intervening delays (1+2)",
        )

    def test_flex_delays_touching_delays(self) -> None:
        period = self.build_match_period(0, 10)
        delays = [
            self.build_delay(time=1, delay=1),  # from 1 -> 2
            self.build_delay(time=2, delay=1),  # from 2 -> 3
        ]
        clock = MatchPeriodClock(period, delays)
        self.assertCurrentTime(clock, 0, "Should start at the start of the period")

        # No flexing, delays are after the spacing starts
        self.assertApplySpacing(clock, 4, flex=3, expected_recovery=None)

        self.assertCurrentTime(
            clock,
            6,
            "Time should advance by the given amount (3) plus the size of the "
            "(future) delays it meets",
        )

    # Flex less than the delays -- should partially absorb the delays

    def test_flex_lt_delays_with_delays(self) -> None:
        period = self.build_match_period(0, 50)
        delays = [
            self.build_delay(time=0, delay=2),  # seen, absorbed
            self.build_delay(time=1, delay=2),  # seen, absorbed
            self.build_delay(time=9, delay=2),  # future, ignored initially
        ]
        clock = MatchPeriodClock(period, delays)
        clock.advance_time(datetime.timedelta(seconds=1))   # plus delays (4)
        self.assertCurrentTime(clock, 5, "Should be after the initial delays")

        # Absorbs some of the delays which were already "expended", but not the
        # one which is in the future.
        self.assertApplySpacing(clock, 4, flex=1, expected_recovery=1)

        self.assertCurrentTime(
            clock,
            8,
            "Time should advance by the given amount (4) minus a portion of the "
            "historic delays (1)",
        )

        # Doesn't absorb any of the delay which happens "during" this spacing,
        # but should absorb some of the previous delay
        self.assertApplySpacing(clock, 3, flex=1, expected_recovery=1)

        self.assertCurrentTime(
            clock,
            12,
            "Time should advance by the given amount (3) minus a portion of the "
            "historic delays (1) plus the size of the delay it meets (2)",
        )

        # Absorbs a portion of the historic delays
        self.assertApplySpacing(clock, 2, flex=1, expected_recovery=1)

        self.assertCurrentTime(
            clock,
            13,
            "Time should advance by the given amount (3) minus a portion of the "
            "historic delays (1)",
        )

        # Recovers from the previous delays (1+2), with some space left over
        self.assertApplySpacing(clock, 5, flex=4, expected_recovery=3)

        self.assertCurrentTime(
            clock,
            15,
            "Time should advance by the given amount (5) minus the historic delays (3)",
        )

        # no flex needed, we're on track
        self.assertApplySpacing(clock, 2, flex=1, expected_recovery=None)

        self.assertCurrentTime(
            clock,
            17,
            "Time should advance by the given amount (2) only; there are no "
            "remaining delays",
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

        for _ in clock.iterslots(2):
            slots.append(clock.current_time)
            if first_time:
                # Advance an extra 3 the first time
                clock.advance_time(3)
                # Now at 5
                first_time = False

        expected = [0, 5]
        self.assertEqual(expected, slots)
