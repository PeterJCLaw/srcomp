from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import (
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


LeagueMatches = NewType('LeagueMatches', dict[int, dict[ArenaName, list[TLA | None]]])


class LeagueData(TypedDict):
    matches: LeagueMatches


class ExtraSpacingData(TypedDict):
    match_numbers: str
    duration: int
    """
    Duration of the spacing, in seconds.
    """


class DelayData(TypedDict):
    delay: int
    time: datetime.datetime


class MatchSlotLengthsData(TypedDict):
    """Lengths of matches in seconds"""
    pre: int
    match: int
    post: int
    total: int


class StagingTimingsData(TypedDict):
    """
    Staging times. Measured in seconds _before_ the _actual_ start
    of the match (rather than its slot).
    """

    opens: int
    """The earliest teams can present themselves for a match"""
    closes: int
    """The time by which teams _must_ be in staging"""
    duration: int
    """How long staging is open for; equal to `opens - closes`"""

    signal_shepherds: Mapping[RegionName, int]
    """
    How long before the start of the match to signal to shepherds they
    should start looking for teams. A mapping of shepherding zones to
    offset values.
    """

    signal_teams: int
    """
    How long before the start of the match to signal to teams they should
    go to staging.
    """


class MatchPeriodData(TypedDict):
    start_time: datetime.datetime
    end_time: datetime.datetime
    max_end_time: NotRequired[datetime.datetime]
    description: str


class MatchPeriodsData(TypedDict):
    league: list[MatchPeriodData]
    knockout: list[MatchPeriodData]


class ScheduleLeagueData(TypedDict):
    extra_spacing: list[ExtraSpacingData]
    """
    Extra spacing before an arbitrary set of matches
    This value is ignored for matches which occur at the start of a period
    since no additional time is needed there. While it might seem nicer
    to require the user to change the values in here, delays can push matches
    from one period to the next which would make it hard for the user to
    keep this up to date.
    """


class KnockoutSingleArenaData(TypedDict):
    """Options for putting last few rounds in one arena"""

    rounds: int
    """Number of final rounds to put in a single arena"""

    arenas: list[ArenaName]


class KnockoutBracketData(TypedDict):
    name: str
    """The internal identifier of a knockout bracket"""

    display_name: str
    """The internal identifier of a knockout bracket"""


class ScheduleKnockoutData(TypedDict):
    round_spacing: int
    """Time delay between rounds (in seconds)"""
    final_delay: int
    """Extra delay before the final (for build-up and rotating, in seconds)"""
    arity: NotRequired[int]
    """Number of teams taking part"""
    single_arena: KnockoutSingleArenaData

    brackets: NotRequired[list[KnockoutBracketData]]
    """
    Brackets which make up the knockout.

    When omitted a single bracket named 'default' with display name "Knockouts" is used.

    This currently has no bearing on the actual matches and is purely a display consideration.
    """

    static: NotRequired[bool]
    """Whether or not to use the static knockout scheduler (rather than the automatic one)"""


StaticMatchTeamReference = NewType('StaticMatchTeamReference', str)
StaticMatchTeamReference.__doc__ = r"""
A logical reference to a team for pulling into a knockout match.

This supports the following formats:
 - 'S\d+': A seeded team, pulled from the results of the league stage.
 - '\d{3}': A reference to a tie-resolved rank in the results of another match
   within the knockout. The first digit refers to the round number, the second
   to the match number within that round and the last to the rank within the
   results of that match to look for a team. All of these are 0-indexed, so
   '000' is the winner of the first match from the first knockouts round. Ties
   are resolved using the standard league position logic.
 - 'R\d+M\d+P\d+': Alternative spelling of round/match/position reference, this
   supports indices containing more digits but otherwise behaves the same.
"""


class StaticMatchInfo(TypedDict):
    arena: ArenaName
    start_time: datetime.datetime
    teams: list[StaticMatchTeamReference | None]
    display_name: NotRequired[str]
    bracket: NotRequired[str]


class StaticKnockoutRoundData(TypedDict):
    display_name: NotRequired[str]
    matches: Mapping[int, StaticMatchInfo]
    """
    A mapping describing the matches in the round.

    Keys should be 0-indexed numbers identifying the match within the round.
    Match identifiers start from zero for each round.
    """


class StaticKnockoutData(TypedDict):
    rounds: Mapping[int, StaticKnockoutRoundData]
    """
    A mapping describing the rounds in the knockout.

    Keys should be 0-indexed numbers identifying the round.
    """


class LegacyStaticKnockoutData(TypedDict):
    """
    Legacy format for statically specifying a knockout.

    This format is deprecated in favour of ``StaticKnockoutData``, though does
    not have a timeline for removal. Internally knockouts in this format are
    converted to the newer format for ingestion.

    Users may wish to use ``srcomp modernise-static-knockout`` provided by the
    ``sr.comp.cli`` package to upgrade their configurations.
    """

    matches: Mapping[int, Mapping[int, StaticMatchInfo]]
    """
    A mapping describing the rounds & matches in the static knockout.

    Keys should be 0-indexed numbers identifying the round or match
    respectively. Match identifiers start from zero for each round.
    """


class ScheduleData(TypedDict):
    match_slot_lengths: MatchSlotLengthsData
    staging: StagingTimingsData
    timezone: str
    delays: list[DelayData]

    match_periods: MatchPeriodsData
    tiebreaker: NotRequired[datetime.datetime]

    league: ScheduleLeagueData
    knockout: ScheduleKnockoutData

    static_knockout: NotRequired[StaticKnockoutData | LegacyStaticKnockoutData]


AwardsData = NewType('AwardsData', dict[str, Union[TLA, list[TLA]]])


class TeamData(TypedDict):
    name: str
    rookie: NotRequired[bool]
    dropped_out_after: NotRequired[MatchNumber]


class TeamsData(TypedDict):
    teams: Mapping[TLA, TeamData]
