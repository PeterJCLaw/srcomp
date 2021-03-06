"""Classes that are useful for dealing with match periods."""

import datetime
from enum import Enum, unique
from typing import List, Mapping, NamedTuple, NewType, Optional

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
    teams: List[Optional[TLA]]
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
    matches: List[MatchSlot]
    type: MatchType  # noqa:A003

    def __str__(self) -> str:
        return "{} ({}–{})".format(
            self.description,
            self.start_time.strftime('%H:%M'),
            self.end_time.strftime('%H:%M'),
        )
