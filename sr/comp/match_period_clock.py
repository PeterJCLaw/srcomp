"""A clock to manage match periods."""

from __future__ import annotations

import datetime
from typing import Iterable, Iterator

from .match_period import Delay, MatchPeriod


class OutOfTimeException(Exception):
    """
    An exception representing no more time available at the competition to run
    matches.
    """


class MatchPeriodClock:
    """
    A clock for use in scheduling matches within a ``MatchPeriod``.

    It is generally expected that the time information here will be in the form
    of ``datetime`` and ``timedelta`` instances, though any data which can be
    compared and added appropriately should work.

    Delay rules:

    - Only delays which are scheduled after the start of the given period will
      be considered.
    - Delays are cumulative.
    - Delays take effect as soon as their ``time`` is reached.
    """

    @staticmethod
    def delays_for_period(period: MatchPeriod, delays: Iterable[Delay]) -> list[Delay]:
        r"""
        Filter and sort a list of all possible delays to include only those
        which occur after the start of the given `period`.

        :param `.MatchPeriod` period: The period to get the delays for.
        :param list delays: The list of :class:`.Delay`\s to consider.
        :return: A sorted list of delays which occur after the start of the period.
        """

        # Only consider delays which are at the start of the period or later
        valid_delays = [d for d in delays if d.time >= period.start_time]

        # Sort by when the delays occur
        valid_delays.sort(key=lambda d: d.time)

        return valid_delays

    def __init__(self, period: MatchPeriod, delays: Iterable[Delay]):
        """Create a new clock for the given period and collection of delays."""
        self._period = period

        self._delays = self.delays_for_period(period, delays)

        # The current time, including any delays
        self._current_time = period.start_time

        # The total applied delay
        self._total_delay: datetime.timedelta | None = None

        # Apply any delays which occur at the start
        self._apply_delays()

    @property
    def current_time(self) -> datetime.datetime:
        """
        Get the apparent current time. This is a combination of the time which
        has passed (through calls to ``advance_time``) and the delays which
        have occurred.

        Will raise an :class:`.OutOfTimeException` if either:

        - the end of the period has been reached (i.e: the sum of durations
          passed to ``advance_time`` has exceeded the planned duration of the
          period), or
        - the maximum end of the period has been reached (i.e: the current time
          would be after the period's ``max_end_time``).
        """

        ct = self._current_time

        # Ensure we haven't exceeded the maximum time limit
        # (if we have then matches will get pushed into the next period)
        if ct > self._period.max_end_time:
            # we've filled this up to the maximum end time
            raise OutOfTimeException(
                "Current time (including delays) is beyond the maximum end time "
                "of the period. Consider removing matches or delays, or adjusting "
                "the maximum end time.",
            )

        # Ensure we haven't attempted to pack in more time than will
        # fit in this period
        if self._time_without_delays() > self._period.end_time:
            # we've filled up this period
            raise OutOfTimeException(
                "Current time (without delays) is beyond the natural end time "
                "of the period. Consider removing matches or adjusting the "
                "natural end time.",
            )

        return ct

    def advance_time(self, duration: datetime.timedelta) -> None:
        """
        Make a given amount of time pass. This is expected to be called after
        scheduling some matches in order to move to the next timeslot.

        .. note::
           It is assumed that the duration value will always be 'positive',
           i.e. that time will not go backwards. The results of the duration
           value being 'negative' are undefined.
        """

        self._current_time += duration
        self._apply_delays()

    def _apply_delays(self) -> None:
        delays = self._delays
        while len(delays) and delays[0].time <= self._current_time:
            self._apply_delay(delays.pop(0).delay)

    def _apply_delay(self, delay: datetime.timedelta) -> None:
        self._current_time += delay

        if self._total_delay is None:
            self._total_delay = delay
        else:
            self._total_delay += delay

    def _time_without_delays(self) -> datetime.datetime:
        if self._total_delay is None:
            return self._current_time
        else:
            return self._current_time - self._total_delay

    def iterslots(self, slot_duration: datetime.timedelta) -> Iterator[datetime.datetime]:
        """
        Iterate through all the available timeslots of the given size within
        the ``MatchPeriod``, taking into account delays.

        This is equivalent to checking the current_time and repeatedly calling
        ``advance_time`` with the given duration. As a result, it is safe to
        call ``advance_time`` between iterations if additional gaps between
        slots are needed.
        """

        try:
            while True:
                yield self.current_time
                self.advance_time(slot_duration)
        except OutOfTimeException:
            # Reached the end of the period
            pass
