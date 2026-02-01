from __future__ import annotations

import dataclasses
import datetime
import enum
from collections.abc import Collection
from pathlib import Path

from . import yaml_loader
from .match_period import Match
from .matches import MatchSchedule
from .types import MatchNumber, OperationsData, ReleasedMatchData


class MatchState(enum.Enum):
    """
    The state of a match from the perspective of match operations.

    - Matches are initially all `FUTURE`.
    - Once a match is released it will become `RELEASED`.
    - If the current time is past the release threshold for a given match and it
      has not be released, then it is `HELD`.
    """

    FUTURE = 'future'
    HELD = 'held'
    RELEASED = 'released'


@dataclasses.dataclass(frozen=True)
class ArenaTimes:
    release_threshold: datetime.datetime
    start: datetime.datetime
    end: datetime.datetime


@dataclasses.dataclass(frozen=True)
class OperationsMatches:
    time: datetime.datetime
    matches: Collection[Match]
    staging_matches: Collection[Match]
    shepherding_matches: Collection[Match]


class InvalidResetDurationError(ValueError):
    def __init__(
        self,
        release_threshold: datetime.timedelta,
        reset_duration: datetime.timedelta,
    ) -> None:
        super().__init__(release_threshold, reset_duration)
        self.release_threshold = release_threshold
        self.reset_duration = reset_duration

    def __str__(self) -> str:
        return (
            "Match reset duration must be at least as long as the release "
            f"threshold. (threshold: {self.release_threshold}, "
            f"reset duration: {self.reset_duration})"
        )


class InvalidReleasedMatchNumberError(ValueError):
    def __init__(
        self,
        number: MatchNumber,
        final_number: MatchNumber,
    ) -> None:
        super().__init__(number, final_number)
        self.number = number
        self.final_number = final_number

    def __str__(self) -> str:
        return (
            f"Invalid released match number {self.number}, must be in range "
            f"0-{self.final_number}"
        )


class MatchOperations:
    @staticmethod
    def create(path: Path, schedule: MatchSchedule) -> MatchOperations:
        try:
            y = yaml_loader.load(path)
            operations_data: OperationsData = y['operations']

            release_threshold = datetime.timedelta(
                seconds=operations_data['release_threshold'],
            )
            reset_duration = datetime.timedelta(
                seconds=operations_data['reset_duration'],
            )
            released_match = operations_data['released_match']

            return MatchOperations(
                schedule,
                release_threshold=release_threshold,
                reset_duration=reset_duration,
                released_match_data=released_match,
            )
        except FileNotFoundError:
            final_match = schedule.final_match
            return MatchOperations(
                schedule,
                release_threshold=datetime.timedelta(0),
                reset_duration=datetime.timedelta(0),
                released_match_data={
                    'number': final_match.num,
                    'time': final_match.start_time,
                },
            )

    def __init__(
        self,
        schedule: MatchSchedule,
        release_threshold: datetime.timedelta,
        reset_duration: datetime.timedelta,
        released_match_data: ReleasedMatchData | None,
    ) -> None:
        if reset_duration < release_threshold:
            raise InvalidResetDurationError(
                release_threshold=release_threshold,
                reset_duration=reset_duration,
            )

        if released_match_data:
            if released_match_data['number'] not in range(schedule.n_matches()):
                raise InvalidReleasedMatchNumberError(
                    number=released_match_data['number'],
                    final_number=schedule.final_match.num,
                )

        self.schedule = schedule
        self.release_threshold = release_threshold
        self.reset_duration = reset_duration
        self.released_match_data = released_match_data

    @property
    def last_released_match(self) -> MatchNumber | None:
        """The most recently released match."""
        if not self.released_match_data:
            return None
        return self.released_match_data['number']

    def get_arena_times(self, match: Match) -> ArenaTimes:
        match_start = match.start_time + self.schedule.match_slot_lengths['pre']
        return ArenaTimes(
            release_threshold=match_start - self.release_threshold,
            start=match_start,
            end=match_start + self.schedule.match_slot_lengths['match'],
        )

    def get_match_state(self, match: Match, when: datetime.datetime) -> MatchState:
        last_released_match = self.last_released_match
        if last_released_match is not None and match.num <= last_released_match:
            return MatchState.RELEASED

        times = self.get_arena_times(match)
        if times.release_threshold <= when:
            return MatchState.HELD

        return MatchState.FUTURE

    def _get_effective_time(self, when: datetime.datetime) -> datetime.datetime:
        """
        Get the "effective" time for a given wall-clock time.

        The returned value accounts for any unreleased matches and can be safely
        used with queries against the schedule (which is otherwise unaware of
        operationally driven changes).
        """

        # For the next, yet to be released match
        num = (
            self.released_match_data['number'] + 1
            if self.released_match_data
            else 0
        )

        if num >= self.schedule.n_matches():
            # All matches have been released
            return when

        slot = self.schedule.matches[num]
        match = next(iter(slot.values()))

        times = self.get_arena_times(match)
        if times.release_threshold > when:
            # Haven't reached the threshold yet -- all is well
            return when

        # In a held state, things are effectively paused at the release
        # threshold time
        return times.release_threshold

    def get_matches_at(self, when: datetime.datetime) -> OperationsMatches:
        """
        Get all the matches with a useful relation to a given time.

        This accounts for both delays committed to the schedule and ongoing
        operational changes such as non-released matches.
        """

        real_when = when
        when = self._get_effective_time(when)

        matches = []
        staging_matches = []
        shepherding_matches = []

        for slot in self.schedule.matches:
            for match in slot.values():
                if match.start_time <= when < match.end_time:
                    matches.append(match)

                staging_times = self.schedule.get_staging_times(match)

                if when > staging_times['closes']:
                    # Already done staging
                    continue

                if staging_times['opens'] <= when:
                    staging_matches.append(match)

                signal_shepherds = staging_times['signal_shepherds']
                if signal_shepherds:
                    first_signal = min(signal_shepherds.values())
                    if first_signal <= when:
                        shepherding_matches.append(match)

        return OperationsMatches(
            time=real_when,
            matches=matches,
            staging_matches=staging_matches,
            shepherding_matches=shepherding_matches,
        )
