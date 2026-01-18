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
class CurrentMatches:
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
                released_match=released_match,
            )
        except FileNotFoundError:
            final_match = schedule.final_match
            return MatchOperations(
                schedule,
                release_threshold=datetime.timedelta(0),
                reset_duration=datetime.timedelta(0),
                released_match={
                    'number': final_match.num,
                    'time': final_match.start_time,
                },
            )

    def __init__(
        self,
        schedule: MatchSchedule,
        release_threshold: datetime.timedelta,
        reset_duration: datetime.timedelta,
        released_match: ReleasedMatchData | None,
    ) -> None:
        if reset_duration < release_threshold:
            raise InvalidResetDurationError(
                release_threshold=release_threshold,
                reset_duration=reset_duration,
            )

        if released_match:
            if released_match['number'] not in range(schedule.n_matches()):
                raise InvalidReleasedMatchNumberError(
                    number=released_match['number'],
                    final_number=schedule.final_match.num,
                )

        self.schedule = schedule
        self.release_threshold = release_threshold
        self.reset_duration = reset_duration
        self.released_match_data = released_match

    def get_arena_times(self, match: Match) -> ArenaTimes:
        match_start = match.start_time + self.schedule.match_slot_lengths['pre']
        return ArenaTimes(
            release_threshold=match_start - self.release_threshold,
            start=match_start,
            end=match_start + self.schedule.match_slot_lengths['match'],
        )

    def get_match_state(self, match: Match) -> MatchState:
        if self.released_match_data and match.num <= self.released_match_data['number']:
            # TODO: emit a warning if a released match slot hasn't started yet?
            # Perhaps a "validation" warning?
            return MatchState.RELEASED

        times = self.get_arena_times(match)
        if times.release_threshold <= self.schedule.datetime_now:
            return MatchState.HELD

        return MatchState.FUTURE

    def get_current_matches(self, when: datetime.datetime) -> CurrentMatches:
        """
        Get all the matches with a useful relation to the current time.

        The time being passed in should always be the current time, however a
        specific value may be passed to support cases where a single timestamp
        is used for several separate queries against the compstate.
        """

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

        return CurrentMatches(
            time=when,
            matches=matches,
            staging_matches=staging_matches,
            shepherding_matches=shepherding_matches,
        )
