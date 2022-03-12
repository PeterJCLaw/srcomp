import datetime
from typing import Dict, Mapping, Optional, Sequence

from dateutil.tz import UTC

from sr.comp.match_period import Match, MatchType
from sr.comp.types import (
    ArenaName,
    GamePoints,
    MatchNumber,
    ScoreData,
    ScoreTeamData,
    TLA,
)


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


# Not strictly a factory, but we don't have a utils file yet. This class is
# tightly coupled to the results returned by build_score_data anyway.
class FakeScorer:
    def __init__(
        self,
        score_data: Mapping[TLA, ScoreTeamData],
        arena_data_unused: Optional[object] = None,
    ) -> None:
        self.score_data = score_data

    def calculate_scores(self) -> Dict[TLA, GamePoints]:
        scores = {}
        for team, info in self.score_data.items():
            scores[team] = info['score']  # type: ignore[typeddict-item]
        return scores


def build_score_data(num: int = 123, arena: str = 'A') -> ScoreData:
    return ScoreData({
        'match_number': MatchNumber(num),
        'arena_id': ArenaName(arena),
        'teams': {
            # TypedDicts don't have a way to allow for *extra* keys, which we do
            # want to have here -- these dictionaries are the actual scoring
            # data for the game and so contain arbitrary other keys.
            TLA('JMS'): {  # type: ignore[typeddict-item]
                'score': 4,
                'disqualified': True,
                'zone': 3,
            },
            TLA('PAS'): {  # type: ignore[typeddict-item]
                'score': 0,
                'present': False,
                'zone': 4,
            },
            TLA('RUN'): {  # type: ignore[typeddict-item]
                'score': 8,
                'zone': 1,
            },
            TLA('ICE'): {  # type: ignore[typeddict-item]
                'score': 2,
                'zone': 2,
            },
        },
    })
