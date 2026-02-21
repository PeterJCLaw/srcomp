from __future__ import annotations

import datetime
from collections.abc import Collection
from typing import Protocol, TypedDict

from sr.comp.match_period import Delay, MatchSlot
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
