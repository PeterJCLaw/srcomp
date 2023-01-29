"""
Calculation of winners of awards.

The awards calculated are:

 * 1st place,
 * 2nd place,
 * 3rd place,
 * Rookie award (rookie team with highest league position).
"""

from __future__ import annotations

from enum import Enum, unique
from pathlib import Path
from typing import List, Mapping

from league_ranker import RankedPosition

from . import yaml_loader
from .match_period import Match, MatchType
from .scores import InvalidTeam, Scores
from .teams import Team
from .types import AwardsData, MatchNumber, TLA


@unique
class Award(Enum):
    """
    Award types.

    These correspond with awards as specified in the rulebook.
    """

    first = 'first'          # First place
    second = 'second'        # Second place
    third = 'third'          # Third place
    rookie = 'rookie'        # Rookie award
    committee = 'committee'  # Committee award
    image = 'image'          # Robot and Team Image award
    movement = 'movement'    # First Movement award
    web = 'web'              # Online Presence award


Winners = Mapping[Award, List[TLA]]


def _compute_main_awards(scores: Scores, final_match_info: Match) -> Winners:
    """Compute awards resulting from the grand finals."""
    last_match_key = (final_match_info.arena, final_match_info.num)

    game_positions = scores.knockout.game_positions
    if final_match_info.type == MatchType.tiebreaker:
        game_positions = scores.tiebreaker.game_positions

    try:
        positions = game_positions[last_match_key]
    except KeyError:
        # We haven't scored the last match yet
        return {}
    awards = {}
    for award, key in (
        (Award.first, RankedPosition(1)),
        (Award.second, RankedPosition(2)),
        (Award.third, RankedPosition(3)),
    ):
        candidates = positions.get(key, ())
        awards[award] = sorted(candidates)

    if not awards[Award.third] and len(final_match_info.teams) == 2:
        # Look in the previous match to find the third place
        final_key = (final_match_info.arena, MatchNumber(final_match_info.num - 1))
        positions = scores.knockout.game_positions[final_key]

        candidates = positions.get(RankedPosition(3), ())
        awards[Award.third] = sorted(candidates)

    return awards


def _compute_rookie_award(scores: Scores, teams: Mapping[TLA, Team]) -> Winners:
    """Compute the winner of the rookie award."""
    rookie_positions = {
        team: position
        for team, position in scores.league.positions.items()
        if teams[team].rookie
    }
    # It's possible there are no rookie teams, in which case nobody gets
    # the award.
    if not rookie_positions:
        return {Award.rookie: []}
    # Position go from 1 upwards (1 being first), so the best is the minimum
    best_position = min(rookie_positions.values())
    return {
        Award.rookie: sorted(
            team
            for team, position in rookie_positions.items()
            if position == best_position
        ),
    }


def _compute_explicit_awards(path: Path, teams: Mapping[TLA, Team]) -> Winners:
    """Compute awards explicitly provided in the compstate repo."""
    if not path.exists():
        return {}

    explicit_awards: AwardsData = yaml_loader.load(path)
    assert explicit_awards, "Awards file should not be present if empty."

    awards = {
        Award(key): [value] if isinstance(value, str) else value
        for key, value in explicit_awards.items()
    }

    for award_teams in awards.values():
        for tla in award_teams:
            if tla not in teams:
                raise InvalidTeam(tla, str(path))

    return awards


def compute_awards(
    scores: Scores,
    final_match: Match,
    teams: Mapping[TLA, Team],
    path: Path | None = None,
) -> Winners:
    """
    Compute the awards handed out from configuration.

    :param sr.comp.scores.Scores scores: The scores.
    :param Match final_match: The match to use as the final.
    :param dict teams: A mapping from TLAs to :class:`sr.comp.teams.Team`
                       objects.
    :return: A dictionary of :class:`Award` types to TLAs is returned. This may
             not have a key for any award type that has not yet been
             determined.
    """

    awards: dict[Award, list[TLA]] = {}
    awards.update(_compute_main_awards(scores, final_match))
    awards.update(_compute_rookie_award(scores, teams))
    if path is not None:
        awards.update(_compute_explicit_awards(path, teams))
    return awards
