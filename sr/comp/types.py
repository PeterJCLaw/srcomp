from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, NewType, runtime_checkable, Union
from typing_extensions import NotRequired, Protocol, TypedDict

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
