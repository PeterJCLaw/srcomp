"""Utilities for working with scores."""

from __future__ import annotations

import dataclasses
from collections import OrderedDict
from functools import total_ordering
from pathlib import Path
from typing import cast, Iterable, Iterator, Mapping, NewType, TypeVar

import league_ranker as ranker
from league_ranker import LeaguePoints, RankedPosition

from . import yaml_loader
from .match_period import Match, MatchType
from .types import (
    ExternalScoreData,
    GamePoints,
    MatchId,
    MatchNumber,
    ScoreData,
    ScorerType,
    TLA,
    ValidatingScorer,
)

T = TypeVar('T')
TBaseScores = TypeVar('TBaseScores', bound='BaseScores')
TKnockoutScores = TypeVar('TKnockoutScores', bound='KnockoutScores')

LeaguePosition = NewType('LeaguePosition', int)
LeaguePositions = Mapping[TLA, LeaguePosition]


class InvalidTeam(Exception):
    """An exception that occurs when a score contains an invalid team."""

    def __init__(self, tla: TLA, context: str) -> None:
        super().__init__(f"Team {tla} (found in {context}) does not exist.")
        self.tla = tla


class DuplicateScoresheet(Exception):
    """
    An exception that occurs if two scoresheets for the same match have been
    entered.
    """

    def __init__(self, match_id: MatchId) -> None:
        super().__init__(f"Scoresheet for {match_id} has already been added.")
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
    def _ordering_key(self) -> tuple[int, int]:
        # Sort lexicographically by league points, then game points
        return self.league_points, self.game_points

    def add_game_points(self, score: GamePoints) -> GamePoints:
        self.game_points = GamePoints(self.game_points + score)
        return self.game_points

    def add_league_points(self, points: ranker.LeaguePoints) -> ranker.LeaguePoints:
        self.league_points = ranker.LeaguePoints(self.league_points + points)
        return self.league_points

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, type(self)) and
            self._ordering_key == other._ordering_key
        )

    # total_ordering doesn't provide this!
    def __ne__(self, other: object) -> bool:
        return not (self == other)

    def __lt__(self, other: TeamScore) -> bool:
        if not isinstance(other, TeamScore):
            return NotImplemented  # type: ignore[unreachable]

        return self._ordering_key < other._ordering_key

    def __repr__(self) -> str:
        return f'TeamScore({self.league_points!r}, {self.game_points!r})'


@dataclasses.dataclass(frozen=True)
class MatchScore:
    match_id: MatchId

    game: Mapping[TLA, GamePoints]
    normalised: Mapping[TLA, LeaguePoints]
    ranking: Mapping[TLA, RankedPosition]


def results_finder(root: Path) -> Iterator[Path]:
    """An iterator that finds score sheet files."""

    for name in root.glob('*'):
        if not name.is_dir():
            continue

        yield from name.glob('*.yaml')


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
        # TODO(python-upgrade): move to using runtime_checkable once we're Python 3.8+ only.
        scorer = cast(ValidatingScorer, scorer)
        scorer.validate(extra_data)

    return scores


def degroup(grouped_positions: Mapping[T, Iterable[TLA]]) -> OrderedDict[TLA, T]:
    """
    Given a mapping of positions to collections of teams at that position,
    returns an :class:`OrderedDict` of teams to their positions.

    Where more than one team has a given position, they are sorted before
    being inserted.
    """

    positions = OrderedDict()
    for pos, teams in grouped_positions.items():
        for tla in sorted(teams):
            positions[tla] = pos
    return positions


def load_scores_data(result_dir: Path) -> Iterator[ScoreData]:
    # Find the scores for each match
    for result_file in results_finder(result_dir):
        yield yaml_loader.load(result_file)


def load_external_scores_data(result_dir: Path) -> Iterator[ExternalScoreData]:
    for result_file in result_dir.glob('*.yaml'):
        raw = yaml_loader.load(result_file)
        yield from raw['scores']


# The scorer that these classes consume should be a class that is compatible
# with libproton in its Proton 2.0.0-rc1 form.
# See https://github.com/PeterJCLaw/proton and
# http://srobo.org/cgit/comp/libproton.git.
class BaseScores:
    """
    A generic class that holds scores.

    :param iterable scores_data: A collection of loaded score sheet data.
    :param dict teams: The teams in the competition.
    :param dict scorer: The scorer logic.
    :param int num_teams_per_arena: The usual number of teams per arena.
    """

    def __init__(
        self,
        scores_data: Iterable[ScoreData],
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
    ) -> None:
        self._scorer = scorer
        self._num_corners = num_teams_per_arena

        self.game_points: dict[MatchId, Mapping[TLA, GamePoints]] = {}
        r"""
        Game points data for each match. Keys are tuples of the form
        ``(arena_id, match_num)``, values are :class:`dict`\s mapping
        TLAs to the number of game points they scored.
        """

        self.game_positions: dict[MatchId, Mapping[RankedPosition, set[TLA]]] = {}
        r"""
        Game position data for each match. Keys are tuples of the form
        ``(arena_id, match_num)``, values are :class:`dict`\s mapping
        ranked positions (i.e: first is `1`, etc.) to an iterable of TLAs
        which have that position. Based solely on teams' game points.
        """

        self.ranked_points: dict[MatchId, dict[TLA, ranker.LeaguePoints]] = {}
        r"""
        Normalised (aka 'league') points earned in each match. Keys are
        tuples of the form ``(arena_id, match_num)``, values are
        :class:`dict`\s mapping TLAs to the number of normalised points
        they would earn for that match.
        """

        # Start with 0 points for each team
        self.teams: Mapping[TLA, TeamScore] = {x: TeamScore() for x in teams}
        """
        Points for each team earned during this portion of the competition.
        Maps TLAs to :class:`.TeamScore` instances.
        """

        for score_data in scores_data:
            self._load_score_data(score_data)

        # Sum the game for each team
        for match_id, match in self.game_points.items():
            for tla, score in match.items():
                if tla not in self.teams:
                    raise InvalidTeam(tla, "score for match {}{}".format(*match_id))
                self.teams[tla].add_game_points(score)

    def _load_score_data(self, score_data: ScoreData) -> None:
        match_id = (score_data['arena_id'], score_data['match_number'])
        if match_id in self.game_points:
            raise DuplicateScoresheet(match_id)

        game_points = get_validated_scores(self._scorer, score_data)
        self.game_points[match_id] = game_points

        # Build the disqualification dict
        dsq = []
        for tla, team_info in score_data['teams'].items():
            # disqualifications and non-presence are effectively the same
            # in terms of league points awarding.
            if (
                team_info.get('disqualified', False) or
                not team_info.get('present', True)
            ):
                dsq.append(tla)

        positions = ranker.calc_positions(game_points, dsq)
        self.game_positions[match_id] = positions
        self.ranked_points[match_id] = \
            ranker.calc_ranked_points(positions, dsq, self._num_corners)

    @property
    def last_scored_match(self) -> MatchNumber | None:
        """The most match with the highest id for which we have score data."""
        if len(self.ranked_points) == 0:
            return None
        matches = self.ranked_points.keys()
        return max(num for arena, num in matches)

    def get_rankings(self, match: Match) -> Mapping[TLA, RankedPosition]:
        """
        Return a mapping of TLAs to ranked positions for the given match.

        This is an internal API -- most consumers should use
        ``Scores.get_scores`` instead.
        """
        match_id = (match.arena, match.num)
        return degroup(self.game_positions[match_id])


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
        scores_data: Iterable[ScoreData],
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
        extra: Mapping[TLA, TeamScore] | None = None,
    ):
        super().__init__(scores_data, teams, scorer, num_teams_per_arena)

        if extra:
            for tla, score in extra.items():
                try:
                    team_score = self.teams[tla]
                except KeyError:
                    raise InvalidTeam(tla, "extra league points data") from None

                team_score.add_game_points(score.game_points)
                team_score.add_league_points(score.league_points)

        # Sum the league scores for each team
        for match_id, match in self.ranked_points.items():
            for tla, points in match.items():
                if tla not in self.teams:
                    raise InvalidTeam(tla, "ranked score for match {}{}".format(*match_id))
                self.teams[tla].add_league_points(points)

        self.positions = self.rank_league(self.teams)
        r"""
        An :class:`.OrderedDict` of TLAs to :class:`sr.comp.scores.LeaguePosition`\s.
        """


class KnockoutScores(BaseScores):
    """A class which holds knockout scores."""

    @staticmethod
    def calculate_ranking(
        match_points: Mapping[TLA, ranker.LeaguePoints],
        league_positions: LeaguePositions,
    ) -> dict[TLA, RankedPosition]:
        """
        Get a ranking of the given match's teams.

        :param match_points: A map of TLAs to (normalised) scores.
        :param league_positions: A map of TLAs to league positions.
        """

        def key(tla: TLA, points: ranker.LeaguePoints) -> tuple[ranker.LeaguePoints, int]:
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
        scores_data: Iterable[ScoreData],
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
        league_positions: LeaguePositions,
    ):
        super().__init__(scores_data, teams, scorer, num_teams_per_arena)

        self.resolved_positions = {}
        r"""
        Position data for each match which includes adjustment for ties.
        Keys are tuples of the form ``(arena_id, match_num)``, values are
        :class:`.OrderedDict`\s mapping TLAs to the ranked position (i.e:
        first is `1`, etc.) of that team, with the winning team in the
        start of the list of keys. Tie resolution is done by league position.
        """

        # Calculate resolve positions for each scored match
        for match_id, match_points in self.ranked_points.items():
            positions = self.calculate_ranking(match_points, league_positions)
            self.resolved_positions[match_id] = positions

    def get_rankings(self, match: Match) -> Mapping[TLA, RankedPosition]:
        """
        Return a mapping of TLAs to ranked positions for the given match.

        This is an internal API -- most consumers should use
        ``Scores.get_scores`` instead.
        """

        if match.use_resolved_ranking:
            match_id = (match.arena, match.num)
            return self.resolved_positions[match_id]

        return super().get_rankings(match)


class TiebreakerScores(KnockoutScores):
    pass


def load_external_scores(
    scores_data: Iterable[ExternalScoreData],
    teams: Iterable[TLA],
) -> Mapping[TLA, TeamScore]:
    """
    Mechanism to import additional scores from an external source.

    This provides flexibility in the sources of score data.
    """

    scores = {x: TeamScore() for x in teams}

    for entry in scores_data:
        tla = TLA(entry['team'])
        try:
            team_score = scores[tla]
        except KeyError:
            raise InvalidTeam(tla, "external scores data") from None

        game_points = entry.get('game_points')
        if game_points:
            team_score.add_game_points(GamePoints(game_points))

        team_score.add_league_points(LeaguePoints(entry['league_points']))

    return scores


class Scores:
    """
    A simple class which stores references to the league and knockout scores.
    """

    @classmethod
    def load(
        cls,
        root: Path,
        teams: Iterable[TLA],
        scorer: ScorerType,
        num_teams_per_arena: int,
    ) -> Scores:
        external_scores = load_external_scores(
            load_external_scores_data(root / 'external'),
            teams,
        )

        league = LeagueScores(
            load_scores_data(root / 'league'),
            teams,
            scorer,
            num_teams_per_arena,
            extra=external_scores,
        )

        knockout = KnockoutScores(
            load_scores_data(root / 'knockout'),
            teams,
            scorer,
            num_teams_per_arena,
            league.positions,
        )

        tiebreaker = TiebreakerScores(
            load_scores_data(root / 'tiebreaker'),
            teams,
            scorer,
            num_teams_per_arena,
            league.positions,
        )

        return cls(league, knockout, tiebreaker)

    def __init__(
        self,
        league: LeagueScores,
        knockout: KnockoutScores,
        tiebreaker: TiebreakerScores,
    ) -> None:
        self.league = league
        """
        The :class:`LeagueScores` for the competition.
        """

        self.knockout = knockout
        """
        The :class:`KnockoutScores` for the competition.
        """

        self.tiebreaker = tiebreaker
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

    def get_scores(self, match: Match) -> MatchScore | None:
        """
        Get the scores for a given match.

        Parameters
        ----------
        match : sr.comp.match_period.Match
            A match.

        Returns
        -------
        MatchScore | None
            An object describing the scores for the match, if scores have been
            recorded yet. Otherwise None.
        """

        scores = {
            MatchType.league: self.league,
            MatchType.knockout: self.knockout,
            MatchType.tiebreaker: self.tiebreaker,
        }[match.type]

        match_id = (match.arena, match.num)
        if match_id not in scores.game_points:
            return None

        return MatchScore(
            match_id,
            game=scores.game_points[match_id],
            normalised=scores.ranked_points[match_id],
            ranking=scores.get_rankings(match),
        )
