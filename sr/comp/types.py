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

ScoreTeamData = TypedDict('ScoreTeamData', {
    'disqualified': bool,
    'present': bool,
    # Plus other keys which are used to actually convey the score data, but
    # which we must not rely on and should not care about. There isn't a way to
    # represent that easily in Python's type system though.
})

ScoreData = TypedDict('ScoreData', {
    'arena_id': ArenaName,
    'match_number': MatchNumber,
    'teams': Dict[TLA, ScoreTeamData],
    'arena_zones': Optional[ScoreArenaZonesData],
    'other': Optional[ScoreOtherData],
})


class SimpleScorer(Protocol):
    def __init__(
        self,
        teams_data: Dict[TLA, ScoreTeamData],
        arena_data: Optional[ScoreArenaZonesData],
    ) -> None:
        # pylint: disable=super-init-not-called
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

DeploymentsData = TypedDict('DeploymentsData', {
    'deployments': List[str],
})

ShepherdData = TypedDict('ShepherdData', {
    'name': ShepherdName,
    'colour': Colour,
    'regions': List[RegionName],
})
ShepherdingData = TypedDict('ShepherdingData', {
    'shepherds': List[ShepherdData],
})
ShepherdingArea = TypedDict('ShepherdingArea', {
    'name': ShepherdName,
    'colour': Colour,
})

RegionData = TypedDict('RegionData', {
    'name': RegionName,
    'display_name': str,
    'description': str,
    'teams': List[TLA],
})
LayoutData = TypedDict('LayoutData', {
    'teams': List[RegionData],
})
Region = TypedDict('Region', {
    'name': RegionName,
    'display_name': str,
    'description': str,
    'teams': List[TLA],
    'shepherds': ShepherdingArea,
})


LeagueMatches = NewType('LeagueMatches', Dict[int, Dict[ArenaName, List[TLA]]])

LeagueData = TypedDict('LeagueData', {
    'matches': LeagueMatches,
})


ExtraSpacingData = TypedDict('ExtraSpacingData', {
    'match_numbers': str,
    'duration': int,
})

DelayData = TypedDict('DelayData', {
    'delay': int,
    'time': datetime.datetime,
})


AwardsData = NewType('AwardsData', Dict[str, Union[TLA, List[TLA]]])
