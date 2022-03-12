import datetime
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    NewType,
    Optional,
    Tuple,
    Type,
    Union,
)
from typing_extensions import Protocol, TypedDict

TLA = NewType('TLA', str)

# A CSS colour (e.g: '#123456' or 'blue')
Colour = NewType('Colour', str)

ArenaName = NewType('ArenaName', str)

MatchNumber = NewType('MatchNumber', int)
MatchId = Tuple[ArenaName, MatchNumber]

YAMLData = Any

# Proton protocol types

GamePoints = NewType('GamePoints', int)

ScoreArenaZonesData = NewType('ScoreArenaZonesData', object)
ScoreOtherData = NewType('ScoreOtherData', object)


class ScoreTeamData(TypedDict, total=False):
    disqualified: bool
    present: bool

    # Unused by SRComp
    zone: int


class _ScoreData(TypedDict):
    arena_id: ArenaName
    match_number: MatchNumber
    teams: Dict[TLA, ScoreTeamData]


class ScoreData(_ScoreData, total=False):
    arena_zones: ScoreArenaZonesData
    other: ScoreOtherData


class SimpleScorer(Protocol):
    def __init__(
        self,
        teams_data: Dict[TLA, ScoreTeamData],
        arena_data: Optional[ScoreArenaZonesData],
    ) -> None:
        ...

    def calculate_scores(self) -> Mapping[TLA, GamePoints]:
        ...


class ValidatingScorer(SimpleScorer, Protocol):
    def validate(self, extra_data: Optional[ScoreOtherData]) -> None:
        ...


Scorer = Union[ValidatingScorer, SimpleScorer]
ScorerType = Type[Union[ValidatingScorer, SimpleScorer]]


# Locations within the Venue

RegionName = NewType('RegionName', str)
ShepherdName = NewType('ShepherdName', str)


# TypeDicts with names ending `Data` represent the raw structure expected in
# files of that name.

class DeploymentsData(TypedDict):
    deployments: List[str]


class ShepherdData(TypedDict):
    name: ShepherdName
    colour: Colour
    regions: List[RegionName]


class ShepherdingData(TypedDict):
    shepherds: List[ShepherdData]


class ShepherdingArea(TypedDict):
    name: ShepherdName
    colour: Colour


class RegionData(TypedDict):
    name: RegionName
    display_name: str
    description: str
    teams: List[TLA]


class LayoutData(TypedDict):
    teams: List[RegionData]


class Region(TypedDict):
    name: RegionName
    display_name: str
    description: str
    teams: List[TLA]
    shepherds: ShepherdingArea


LeagueMatches = NewType('LeagueMatches', Dict[int, Dict[ArenaName, List[TLA]]])


class LeagueData(TypedDict):
    matches: LeagueMatches


class ExtraSpacingData(TypedDict):
    match_numbers: str
    duration: int


class DelayData(TypedDict):
    delay: int
    time: datetime.datetime


AwardsData = NewType('AwardsData', Dict[str, Union[TLA, List[TLA]]])
