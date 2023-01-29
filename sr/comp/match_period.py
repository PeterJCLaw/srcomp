"""Classes that are useful for dealing with match periods."""

from __future__ import annotations

import datetime
from enum import Enum, unique
from typing import Mapping, NamedTuple, NewType

from .types import ArenaName, MatchNumber, TLA


class Delay(NamedTuple):
    delay: datetime.timedelta
    time: datetime.datetime


@unique
class MatchType(Enum):
    league = 'league'
    knockout = 'knockout'
    tiebreaker = 'tiebreaker'


class Match(NamedTuple):
    num: MatchNumber
    display_name: str
    arena: ArenaName
    teams: list[TLA | None]
    start_time: datetime.datetime
    end_time: datetime.datetime
    type: MatchType  # noqa:A003
    use_resolved_ranking: bool


MatchSlot = NewType('MatchSlot', Mapping[ArenaName, Match])


class MatchPeriod(NamedTuple):
    start_time: datetime.datetime
    end_time: datetime.datetime
    max_end_time: datetime.datetime
    description: str
    matches: list[MatchSlot]
    type: MatchType  # noqa:A003

    def __str__(self) -> str:
        return "{} ({}–{})".format(
            self.description,
            self.start_time.strftime('%H:%M'),
            self.end_time.strftime('%H:%M'),
        )
