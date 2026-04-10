from __future__ import annotations

import bisect
import datetime
import random
from collections.abc import Iterable, Mapping, Sequence
from typing import TypeVar

from sr.comp.knockout_scheduler.base_scheduler import (
    DEFAULT_KNOCKOUT_BRACKET_NAME,
)
from sr.comp.match_period import (
    Delay,
    KnockoutMatch,
    Match,
    MatchSlot,
    MatchType,
)
from sr.comp.types import (
    ArenaName,
    GamePoints,
    MatchNumber,
    ScoreData,
    ScoreTeamData,
    TLA,
)

UTC = datetime.timezone.utc

T = TypeVar('T')


def build_match(
    num: int = 0,
    arena: str = 'main',
    teams: Sequence[TLA | None] = (),
    start_time: datetime.datetime = datetime.datetime(2020, 1, 25, 11, 0, tzinfo=UTC),
    end_time: datetime.datetime = datetime.datetime(2020, 1, 25, 11, 5, tzinfo=UTC),
    type_: MatchType = MatchType.league,
    use_resolved_ranking: bool = False,
    knockout_bracket: str | None = None,
) -> Match:
    if type_ == MatchType.knockout:
        return KnockoutMatch(
            MatchNumber(num),
            f"Match {num}",
            ArenaName(arena),
            list(teams),
            start_time,
            end_time,
            type_,
            use_resolved_ranking,
            knockout_bracket or DEFAULT_KNOCKOUT_BRACKET_NAME,
        )
    elif knockout_bracket is not None:
        raise TypeError("Should not provide 'knockout_bracket' for non-knockout match")

    return Match(
        MatchNumber(num),
        f"Match {num}",
        ArenaName(arena),
        list(teams),
        start_time,
        end_time,
        type_,
        use_resolved_ranking,
    )


# Not strictly a factory, but we don't have a utils file yet. This class is
# tightly coupled to the results returned by build_score_data anyway.
class FakeScorer:
    def __init__(
        self,
        score_data: Mapping[TLA, ScoreTeamData],
        arena_data_unused: object | None = None,
    ) -> None:
        self.score_data = score_data

    def calculate_scores(self) -> dict[TLA, GamePoints]:
        scores = {}
        for team, info in self.score_data.items():
            scores[team] = info['score']  # type: ignore[typeddict-item]
        return scores


def shuffled(items: Iterable[T]) -> Iterable[T]:
    items = list(items)
    random.shuffle(items)
    return items


def build_score_data(
    num: int = 123,
    arena: str = 'A',
    scores: Mapping[str, int] | None = None,
) -> ScoreData:
    if not scores:
        scores = {
            'JMS': 4,
            'PAS': 0,
            'RUN': 8,
            'ICE': 2,
        }

    return ScoreData({
        'match_number': MatchNumber(num),
        'arena_id': ArenaName(arena),
        'teams': {
            # TypedDicts don't have a way to allow for *extra* keys, which we do
            # want to have here -- these dictionaries are the actual scoring
            # data for the game and so contain arbitrary other keys.
            TLA(tla): {  # type: ignore[typeddict-unknown-key]
                'score': score,
                'zone': idx,
            }
            for idx, (tla, score) in enumerate(shuffled(scores.items()))
        },
    })


class FakeSchedule:
    """
    Minimal `MatchSchedule` drop-in, sufficient to meet the `ScheduleHost`
    protocol used by the knockout schedulers.
    """

    def __init__(
        self,
        *,
        delays: list[Delay],
        matches: list[MatchSlot],
        match_duration: datetime.timedelta,
    ):
        self.delays = delays
        self.delays.sort(key=lambda x: x.time)
        self.matches = matches
        self.match_duration = match_duration
        self.n_league_matches = len(matches)

    def _recover_time(self, recovered_time: Delay) -> None:
        bisect.insort(self.delays, recovered_time, key=lambda x: x.time)
