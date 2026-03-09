from __future__ import annotations

import datetime
from collections.abc import Collection, Iterable
from typing import Protocol, TypedDict

from sr.comp.match_period import Delay, Match, MatchSlot
from sr.comp.types import MatchPeriodData


class ScheduleHost(Protocol):
    @property
    def delays(self) -> Collection[Delay]:
        ...

    @property
    def matches(self) -> list[MatchSlot]:
        ...

    @property
    def match_duration(self) -> datetime.timedelta:
        ...

    @property
    def n_league_matches(self) -> int:
        ...


class KnockoutPeriodData(TypedDict):
    knockout: list[MatchPeriodData]


class KnockoutRound(list[Match]):
    """
    A round of matches within the knockout stages.

    Note: for convenience this currently inherits from ``list``. However this is
    liable to change and most of the methods from ``list`` are not considered
    part of the public interface. Consumers should treat this as a ``Sequence``.
    """

    def __init__(self, name: str, matches: Iterable[Match] = ()):
        super().__init__(matches)
        self.name = name
