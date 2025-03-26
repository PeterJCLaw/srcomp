from __future__ import annotations

from typing import Collection, Mapping

import league_ranker
from league_ranker import LeaguePoints, RankedPosition, TZone

from .types import MatchId, Ranker


class LeagueRanker(Ranker):
    """
    Default implementation of a ranker class, wrapping `league-ranker`.
    """

    def calc_ranked_points(
        self,
        positions: Mapping[RankedPosition, Collection[TZone]],
        *,
        disqualifications: Collection[TZone],
        num_zones: int,
        match_id: MatchId,
    ) -> dict[TZone, LeaguePoints]:
        return league_ranker.calc_ranked_points(
            positions,
            disqualifications,
            num_zones,
        )
