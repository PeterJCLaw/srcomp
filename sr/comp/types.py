from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import (
    Any,
    Collection,
    NewType,
    Protocol,
    runtime_checkable,
    TypedDict,
    Union,
)
from typing_extensions import NotRequired

from league_ranker import LeaguePoints, RankedPosition, TZone

TLA = NewType('TLA', str)

# A CSS colour (e.g: '#123456' or 'blue')
Colour = NewType('Colour', str)

ArenaName = NewType('ArenaName', str)

MatchNumber = NewType('MatchNumber', int)
MatchId = tuple[ArenaName, MatchNumber]

YAMLData = Any

# Proton protocol types

GamePoints = NewType('GamePoints', int)

ScoreArenaZonesData = NewType('ScoreArenaZonesData', object)
ScoreOtherData = NewType('ScoreOtherData', object)


class ScoreTeamData(TypedDict):
    disqualified: NotRequired[bool]
    present: NotRequired[bool]

    # Unused by SRComp
    zone: int


class ScoreData(TypedDict):
    arena_id: ArenaName
    match_number: MatchNumber
    teams: Mapping[TLA, ScoreTeamData]

    arena_zones: NotRequired[ScoreArenaZonesData]
    other: NotRequired[ScoreOtherData]


@runtime_checkable
class SimpleScorer(Protocol):
    def __init__(
        self,
        teams_data: Mapping[TLA, ScoreTeamData],
        arena_data: ScoreArenaZonesData | None,
    ) -> None:
        ...

    def calculate_scores(self) -> Mapping[TLA, GamePoints]:
        ...


@runtime_checkable
class ValidatingScorer(SimpleScorer, Protocol):
    def validate(self, extra_data: ScoreOtherData | None) -> None:
        ...


Scorer = Union[ValidatingScorer, SimpleScorer]
ScorerType = type[Union[ValidatingScorer, SimpleScorer]]


class ExternalScoreData(TypedDict):
    """
    The expected YAML data format in "external" scores files is a single root
    key 'scores' whose value is a list of mappings compatible with this type.
    """

    team: str
    game_points: NotRequired[int]
    league_points: int


class Ranker(Protocol):
    """
    Computes ranking information related to the league.

    This is part of providing a hook point for customising the league points
    behaviour. Initially this only supports changing the behaviour of the points
    returned, though we may extend this in future to support other functionality
    currently directly tied to the `league-ranker` package, such as position
    calculation.
    """

    def calc_ranked_points(
        self,
        positions: Mapping[RankedPosition, Collection[TZone]],
        *,
        disqualifications: Collection[TZone],
        num_zones: int,
        match_id: MatchId,
    ) -> dict[TZone, LeaguePoints]:
        """
        Equivalent to `league_ranker.calc_ranked_points`, though with clearer
        argument names and accepting a match id value to enable customisation.
        """
        ...


RankerType = type[Ranker]

# Locations within the Venue

RegionName = NewType('RegionName', str)
ShepherdName = NewType('ShepherdName', str)


# TypeDicts with names ending `Data` represent the raw structure expected in
# files of that name.

class DeploymentsData(TypedDict):
    deployments: list[str]


class ShepherdData(TypedDict):
    name: ShepherdName
    colour: Colour
    regions: list[RegionName]


class ShepherdingData(TypedDict):
    shepherds: list[ShepherdData]


class ShepherdingArea(TypedDict):
    name: ShepherdName
    colour: Colour


class RegionData(TypedDict):
    name: RegionName
    display_name: str
    description: NotRequired[str]
    teams: list[TLA]


class LayoutData(TypedDict):
    teams: list[RegionData]


class Region(TypedDict):
    name: RegionName
    display_name: str
    description: str
    teams: list[TLA]
    shepherds: ShepherdingArea


LeagueMatches = NewType('LeagueMatches', dict[int, dict[ArenaName, list[TLA]]])


class LeagueData(TypedDict):
    matches: LeagueMatches


class ExtraSpacingData(TypedDict):
    match_numbers: str
    duration: int


class DelayData(TypedDict):
    delay: int
    time: datetime.datetime


AwardsData = NewType('AwardsData', dict[str, Union[TLA, list[TLA]]])


class ReleasedMatchData(TypedDict):
    number: MatchNumber
    time: datetime.datetime


class OperationsData(TypedDict):
    """
    Information relating to the operation of matches.
    """

    release_threshold: int
    """
    Duration prior to the start of a match to pause if the match has not been
    "released". In seconds relative to the start of the game (not the slot).
    """

    reset_duration: int
    """
    Duration prior to the start of a match to reset to if the match is "reset".
    In seconds relative to the start of the game (not the slot). Must be greater
    than or equal to `release_threshold`.
    """

    released_match: ReleasedMatchData | None
    """
    Information about the currently released match.

    Either:
      - None, meaning that no matches have been released, or
      - the most recently released match & when it was released

    History is not recorded. Delays are used to correct for "late" releases.
    Resets are performed by changing this to a suitable value for the previous
    match and (if needed) adding a delay.
    """
