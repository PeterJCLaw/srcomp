"""Utilities for working with scores."""

import glob
import os
from collections import OrderedDict
from functools import total_ordering
from typing import (
    cast,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    NewType,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

import league_ranker as ranker
from league_ranker import RankedPosition

from . import yaml_loader
from .types import (
    GamePoints,
    MatchId,
    MatchNumber,
    ScoreData,
    ScorerType,
    TLA,
    ValidatingScorer,
)

T = TypeVar('T')

LeaguePosition = NewType('LeaguePosition', int)
LeaguePositions = Mapping[TLA, LeaguePosition]


class InvalidTeam(Exception):
    """An exception that occurs when a score contains an invalid team."""

    def __init__(self, tla: TLA, context: str) -> None:
        message = "Team {0} (found in {1}) does not exist.".format(tla, context)
        super().__init__(message)
        self.tla = tla


class DuplicateScoresheet(Exception):
    """
    An exception that occurs if two scoresheets for the same match have been
    entered.
    """

    def __init__(self, match_id: MatchId) -> None:
        message = "Scoresheet for {0} has already been added.".format(match_id)
        super().__init__(message)
        self.match_id = match_id


@total_ordering
class TeamScore:
    """
    A team score.

    :param int league: The league points.
    :param int game: The game points.
    """

    def __init__(
        self,
        league: ranker.LeaguePoints = ranker.LeaguePoints(0),
        game: GamePoints = GamePoints(0),
    ):
        self.league_points = league
        self.game_points = game

    @property
    def _ordering_key(self) -> Tuple[int, int]:
        # Sort lexicographically by league points, then game points
        return self.league_points, self.game_points

    def add_game_points(self, score: GamePoints) -> GamePoints:
        self.game_points = GamePoints(self.game_points + score)
        return self.game_points

    def add_league_points(self, points: ranker.LeaguePoints) -> ranker.LeaguePoints:
        self.league_points = ranker.LeaguePoints(self.league_points + points)
        return self.league_points

    def __eq__(self, other: object) -> bool:
        # pylint: disable=protected-access
        return (
            isinstance(other, type(self)) and
            self._ordering_key == other._ordering_key
        )

    # total_ordering doesn't provide this!
    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __lt__(self, other: 'TeamScore') -> bool:
        if not isinstance(other, TeamScore):
            return NotImplemented  # type: ignore[unreachable]

        # pylint: disable=protected-access
        return self._ordering_key < other._ordering_key

    def __repr__(self) -> str:
        return 'TeamScore({0}, {1})'.format(
            self.league_points,
            self.game_points,
        )


def results_finder(root: str) -> Iterator[str]:
    """An iterator that finds score sheet files."""

    for dname in glob.glob(os.path.join(root, "*")):
        if not os.path.isdir(dname):
            continue

        for resfile in glob.glob(os.path.join(dname, "*.yaml")):
            yield resfile


def get_validated_scores(
    scorer_cls: ScorerType,
    input_data: ScoreData,
) -> Mapping[TLA, GamePoints]:
    """
    Helper function which mimics the behaviour from libproton.

    Given a libproton 3.0 (Proton 3.0.0-rc2) compatible class this will
    calculate the scores and validate the input.
    """

    teams_data = input_data['teams']
    arena_data = input_data.get('arena_zones')  # May be absent
    extra_data = input_data.get('other')  # May be absent

    scorer = scorer_cls(teams_data, arena_data)
    scores = scorer.calculate_scores()

    # Also check the validation, if supported. Explicit pre-check so
    # that we don't accidentally hide any AttributeErrors (or similar)
    # which come from inside the method.
    if hasattr(scorer, 'validate'):
        # pylint: disable=fixme
        # TODO: move to using runtime_checkable once we're Python 3.8+ only.
        scorer = cast(ValidatingScorer, scorer)
        scorer.validate(extra_data)

    return scores


def degroup(grouped_positions: Mapping[T, Iterable[TLA]]) -> Dict[TLA, T]:
    """
    Given a mapping of positions to collections ot teams at that position,
    returns an :class:`OrderedDict` of teams to their positions.

    Where more than one team has a given position, they are sorted before
    being inserted.
    """

    positions = OrderedDict()
    for pos, teams in grouped_positions.items():
        for tla in sorted(teams):
            positions[tla] = pos
    return positions


# The scorer that these classes consume should be a class that is compatible
# with libproton in its Proton 2.0.0-rc1 form.
# See https://github.com/PeterJCLaw/proton and
# http://srobo.org/cgit/comp/libproton.git.
class BaseScores:
    """
    A generic class that holds scores.

    :param str resultdir: Where to find score sheet files.
    :param dict teams: The teams in the competition.
    :param dict scorer: The scorer logic.
    :param int num_teams_per_arena: The usual number of teams per arena.
    """

    def __init__(
        self,
        resultdir: str,
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
    ) -> None:
        self._scorer = scorer
        self._num_corners = num_teams_per_arena

        self.game_points = {}  # type: Dict[MatchId, Mapping[TLA, GamePoints]]
        """
        Game points data for each match. Keys are tuples of the form
        ``(arena_id, match_num)``, values are :class:`dict` s mapping
        TLAs to the number of game points they scored.
        """

        self.game_positions = {}  # type: Dict[MatchId, Mapping[RankedPosition, Set[TLA]]]
        """
        Game position data for each match. Keys are tuples of the form
        ``(arena_id, match_num)``, values are :class:`dict` s mapping
        ranked positions (i.e: first is `1`, etc.) to an iterable of TLAs
        which have that position. Based solely on teams' game points.
        """

        self.ranked_points = {}  # type: Dict[MatchId, Dict[TLA, ranker.LeaguePoints]]
        """
        Normalised (aka 'league') points earned in each match. Keys are
        tuples of the form ``(arena_id, match_num)``, values are
        :class:`dict` s mapping TLAs to the number of normalised points
        they would earn for that match.
        """

        self.teams = {}
        """
        Points for each team earned during this portion of the competition.
        Maps TLAs to :class:`.TeamScore` instances.
        """

        # Start with 0 points for each team
        for tla in teams:
            self.teams[tla] = TeamScore()

        # Find the scores for each match
        for resfile in results_finder(resultdir):
            self._load_resfile(resfile)

        # Sum the game for each team
        for match_id, match in self.game_points.items():
            for tla, score in match.items():
                if tla not in self.teams:
                    raise InvalidTeam(tla, "score for match {0}{1}".format(*match_id))
                self.teams[tla].add_game_points(score)

    def _load_resfile(self, fname: str) -> None:
        y = yaml_loader.load(fname)  # type: ScoreData

        match_id = (y['arena_id'], y['match_number'])
        if match_id in self.game_points:
            raise DuplicateScoresheet(match_id)

        game_points = get_validated_scores(self._scorer, y)
        self.game_points[match_id] = game_points

        # Build the disqualification dict
        dsq = []
        for tla, scoreinfo in y['teams'].items():
            # disqualifications and non-presence are effectively the same
            # in terms of league points awarding.
            if (
                scoreinfo.get('disqualified', False) or
                not scoreinfo.get('present', True)
            ):
                dsq.append(tla)

        positions = ranker.calc_positions(game_points, dsq)
        self.game_positions[match_id] = positions
        self.ranked_points[match_id] = \
            ranker.calc_ranked_points(positions, dsq, self._num_corners)

    @property
    def last_scored_match(self) -> Optional[MatchNumber]:
        """The most match with the highest id for which we have score data."""
        if len(self.ranked_points) == 0:
            return None
        matches = self.ranked_points.keys()
        return max(num for arena, num in matches)


class LeagueScores(BaseScores):
    """A class which holds league scores."""

    @staticmethod
    def rank_league(team_scores: Mapping[TLA, TeamScore]) -> LeaguePositions:
        """
        Given a mapping of TLA to TeamScore, returns a mapping of TLA to league
        position which both allows for ties and enables their resolution
        deterministically.
        """

        # Reverse sort the (tla, score) pairs so the biggest scores are at the
        # top. We break perfect ties by TLA, which is not fair but is
        # deterministic.
        # Note that the unfair result is only present within the key ordering
        # of the resulting OrderedDict -- the values it contains will admit
        # to tied values.
        # Both of these are used within the system -- the knockouts need
        # a list of teams to seed with, various awards (and humans) want
        # a result which allows for ties.
        ranking = sorted(
            team_scores.items(),
            key=lambda x: (x[1], x[0]),
            reverse=True,
        )
        positions = OrderedDict()
        pos = 1
        last_score = None
        for i, (tla, score) in enumerate(ranking, start=1):
            if score != last_score:
                pos = i
            positions[tla] = LeaguePosition(pos)
            last_score = score
        return positions

    def __init__(
        self,
        resultdir: str,
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
    ):
        super().__init__(resultdir, teams, scorer, num_teams_per_arena)

        # Sum the league scores for each team
        for match_id, match in self.ranked_points.items():
            for tla, score in match.items():
                if tla not in self.teams:
                    raise InvalidTeam(tla, "ranked score for match {0}{1}".format(*match_id))
                self.teams[tla].add_league_points(score)

        self.positions = self.rank_league(self.teams)
        """
        An :class:`.OrderedDict` of TLAs to :class:`.TeamScore` instances.
        """


class KnockoutScores(BaseScores):
    """A class which holds knockout scores."""

    @staticmethod
    def calculate_ranking(
        match_points: Mapping[TLA, ranker.LeaguePoints],
        league_positions: LeaguePositions,
    ) -> Dict[TLA, RankedPosition]:
        """
        Get a ranking of the given match's teams.

        :param match_points: A map of TLAs to (normalised) scores.
        :param league_positions: A map of TLAs to league positions.
        """

        def key(tla: TLA, points: ranker.LeaguePoints) -> Tuple[ranker.LeaguePoints, int]:
            # Lexicographically sort by game result, then by league position
            # League positions are sorted in the opposite direction
            return points, -league_positions.get(tla, 0)

        # Sort by points with tie resolution
        # Convert the points values to keys
        keyed = {tla: key(tla, points) for tla, points in match_points.items()}

        # Defer to the ranker to calculate positions
        positions = ranker.calc_positions(keyed)

        # Invert the map back to being TLA -> position
        ranking = degroup(positions)

        return ranking

    def __init__(
        self,
        resultdir: str,
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
        league_positions: LeaguePositions,
    ):
        super().__init__(resultdir, teams, scorer, num_teams_per_arena)

        self.resolved_positions = {}
        """
        Position data for each match which includes adjustment for ties.
        Keys are tuples of the form ``(arena_id, match_num)``, values are
        :class:`.OrderedDict` s mapping TLAs to the ranked position (i.e:
        first is `1`, etc.) of that team, with the winning team in the
        start of the list of keys. Tie resolution is done by league position.
        """

        # Calculate resolve positions for each scored match
        for match_id, match_points in self.ranked_points.items():
            positions = self.calculate_ranking(match_points, league_positions)
            self.resolved_positions[match_id] = positions


class TiebreakerScores(KnockoutScores):
    pass


class Scores:
    """
    A simple class which stores references to the league and knockout scores.
    """

    def __init__(
        self,
        root: str,
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
    ) -> None:
        self.root = root

        self.league = LeagueScores(
            os.path.join(root, 'league'),
            teams,
            scorer,
            num_teams_per_arena,
        )
        """
        The :class:`LeagueScores` for the competition.
        """

        self.knockout = KnockoutScores(
            os.path.join(root, 'knockout'),
            teams,
            scorer,
            num_teams_per_arena,
            self.league.positions,
        )
        """
        The :class:`KnockoutScores` for the competition.
        """

        self.tiebreaker = TiebreakerScores(
            os.path.join(root, 'tiebreaker'),
            teams,
            scorer,
            num_teams_per_arena,
            self.league.positions,
        )
        """
        The :class:`TiebreakerScores` for the competition.
        """

        lsm = None
        for scores in (self.tiebreaker, self.knockout, self.league):
            lsm = scores.last_scored_match
            if lsm is not None:
                break

        self.last_scored_match = lsm
        """
        The match with the highest id for which we have score data.
        """
