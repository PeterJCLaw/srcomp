import datetime
from typing import Optional, Sequence

from dateutil.tz import UTC

from sr.comp.match_period import Match, MatchType
from sr.comp.types import ArenaName, MatchNumber, TLA


def build_match(
    num: int = 0,
    arena: str = 'main',
    teams: Sequence[Optional[TLA]] = (),
    start_time: datetime.datetime = datetime.datetime(2020, 1, 25, 11, 0, tzinfo=UTC),
    end_time: datetime.datetime = datetime.datetime(2020, 1, 25, 11, 5, tzinfo=UTC),
    type_: MatchType = MatchType.league,
    use_resolved_ranking: bool = False,
) -> Match:
    return Match(
        MatchNumber(num),
        "Match {n}".format(n=num),
        ArenaName(arena),
        list(teams),
        start_time,
        end_time,
        type_,
        use_resolved_ranking,
    )
