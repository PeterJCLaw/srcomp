from __future__ import annotations

import datetime
import random
from collections.abc import Iterable, Mapping, Sequence
from typing import TypeVar

from sr.comp.match_period import Match, MatchType
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
) -> Match:
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
