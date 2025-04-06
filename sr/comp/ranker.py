from __future__ import annotations

from typing import Collection, Mapping

import league_ranker
from league_ranker import LeaguePoints, RankedPosition, TZone

from .types import MatchId


def default_calc_ranked_points(
    positions: Mapping[RankedPosition, Collection[TZone]],
    *,
    disqualifications: Collection[TZone],
    num_zones: int,
    match_id: MatchId,
) -> dict[TZone, LeaguePoints]:
    """
    Default implementation of `CalcRankedPointsHook`, wrapping `league-ranker`.
    """
    return league_ranker.calc_ranked_points(
        positions,
        disqualifications,
        num_zones,
    )
