import datetime
from typing import Any, Dict, List, Mapping, NewType, Tuple, Type, Union
from typing_extensions import Protocol, TypedDict

TLA = NewType('TLA', str)

# A CSS colour (e.g: '#123456' or 'blue')
Colour = NewType('Colour', str)

ArenaName = NewType('ArenaName', str)

MatchNumber = NewType('MatchNumber', int)
MatchId = Tuple[ArenaName, MatchNumber]

YAMLData = Any

# Proton protocol types

# TODO: is `int` the right base here? Do we even know/care what the actual
# Scorer outputs?
GamePoints = NewType('GamePoints', int)


class SimpleScorer(Protocol):
    # TODO: remove these `Any`s?
    def __init__(self, teams_data: Any, arena_data: Any):
        ...

    def calculate_scores(self) -> Mapping[TLA, GamePoints]:
        ...


class ValidatingScorer(SimpleScorer, Protocol):
    def validate(self, extra_data: Any) -> None:
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
