"""Base for knockout scheduling."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Generic, TypedDict, TypeVar

from ..match_period import Match, MatchPeriod, MatchType
from ..scores import Scores
from ..teams import Team
from ..types import ArenaName, KnockoutBracketData, MatchId, MatchNumber, TLA
from .types import (
    KnockoutBracket,
    KnockoutPeriodData,
    KnockoutRound,
    ScheduleHost,
)

# Use '???' as the "we don't know yet" marker
UNKNOWABLE_TEAM = TLA('???')


class BaseKnockoutScheduleData(TypedDict):
    match_periods: KnockoutPeriodData
    brackets: Sequence[KnockoutBracketData]


TConfig = TypeVar('TConfig', bound=BaseKnockoutScheduleData)

DEFAULT_KNOCKOUT_BRACKET_NAME = 'default'


class BaseKnockoutScheduler(Generic[TConfig]):
    """
    Base class for knockout schedulers offering common functionality.

    :param schedule: The league schedule.
    :param scores: The scores.
    :param dict arenas: The arenas.
    :param dict teams: The teams.
    :param config: Custom configuration for the knockout scheduler.
    """

    @staticmethod
    def _build_brackets(brackets: Sequence[KnockoutBracketData]) -> list[KnockoutBracket]:
        if not brackets:
            return [
                KnockoutBracket(
                    DEFAULT_KNOCKOUT_BRACKET_NAME,
                    display_name="Knockouts",
                ),
            ]

        return [KnockoutBracket(**x) for x in brackets]

    def __init__(
        self,
        schedule: ScheduleHost,
        scores: Scores,
        arenas: Iterable[ArenaName],
        num_teams_per_arena: int,
        teams: Mapping[TLA, Team],
        config: TConfig,
    ) -> None:
        self.schedule = schedule
        self.scores = scores
        self.arenas = arenas
        self.teams = teams
        self.config = config

        self.num_teams_per_arena = num_teams_per_arena
        """
        The number of spaces for teams in an arena.

        This is used in building matches where we don't yet know which teams will
        actually be playing, and for filling in when there aren't enough teams to
        fill the arena.
        """

        self.knockout_brackets = self._build_brackets(self.config['brackets'])
        """
        Brackets which make up the knockout.

        This currently has no bearing on the actual matches and is purely a
        display consideration.
        """

        # The knockout matches appear in the normal matches list
        # but this list provides them in groups of rounds.
        # e.g. self.knockout_rounds[-2] gives the semi-final matches
        # and self.knockout_rounds[-1] gives the final match (in a list)
        # Note that the ordering of the matches within the rounds
        # in this list is important (e.g. self.knockout_rounds[0][0] is
        # will involve the top seed, whilst self.knockout_rounds[0][-1] will
        # involve the second seed).
        self.knockout_rounds: list[KnockoutRound] = []

        period_config = self.config['match_periods']['knockout'][0]
        self.period = MatchPeriod(
            period_config['start_time'],
            period_config['end_time'],
            # The knockouts *must* end on time, so we don't specify a
            # different max_end_time.
            period_config['end_time'],
            period_config['description'],
            [],
            MatchType.knockout,
        )

    def _played_all_league_matches(self) -> bool:
        """
        Check if all league matches have been played.

        :return: :py:bool:`True` if we've played all league matches.
        """

        for arena_matches in self.schedule.matches:
            for match in arena_matches.values():
                if match.type != MatchType.league:
                    continue

                if (match.arena, match.num) not in self.scores.league.game_points:
                    return False

        return True

    @staticmethod
    def get_match_display_name(
        rounds_remaining: int,
        num_within_round: int,
        global_num: MatchNumber,
    ) -> str:
        """
        Get a human-readable match display name.

        :param rounds_remaining: The number of knockout rounds remaining.
        :param num_within_round: The match number within the knockout round.
        :param global_num: The global match number.
        """

        if rounds_remaining == 0:
            display_name = "Final (#{global_num})"
        elif rounds_remaining == 1:
            display_name = "Semi {num_within_round} (#{global_num})"
        elif rounds_remaining == 2:
            display_name = "Quarter {num_within_round} (#{global_num})"
        else:
            display_name = "Match {global_num}"
        return display_name.format(
            num_within_round=num_within_round + 1,
            global_num=global_num,
        )

    @staticmethod
    def get_round_display_name(
        round_number: int,
        rounds_remaining: int,
    ) -> str:
        """
        Get a human-readable knockout round display name.

        :param round_number: The round number within the knockouts.
            This should be a 0-indexed number.
        :param rounds_remaining: The number of knockout rounds remaining.
        """

        if rounds_remaining == 0:
            return "Finals"
        elif rounds_remaining == 1:
            return "Semi Finals"
        elif rounds_remaining == 2:
            return "Quarter Finals"
        return f"Round {round_number}"

    def get_ranking(self, game: Match) -> list[TLA]:
        """
        Get a ranking of the given match's teams.

        :param game: A game.
        """
        match_id: MatchId = (game.arena, game.num)

        # Get the resolved positions if present (will be a tla -> position map)
        positions = self.scores.knockout.resolved_positions.get(match_id, None)

        if positions is None:
            # Given match hasn't been scored yet
            return [
                UNKNOWABLE_TEAM
                for x in game.teams
                if x is not None
            ]

        # Extract just TLAs
        return list(positions.keys())

    def _get_seeds(self) -> list[TLA]:
        """
        Get a list of TLAs ordered by league position, for use in building a
        knockout schedule.

        This will not include any teams who have dropped out prior to the start
        of the league. The top seed will be first in the list.

        If the league has not completed (and thus a seeding is not yet
        available) the list will contain an explicit placeholder TLA, though the
        length of the list will be as correct based on the dropouts so far.
        """
        first_knockout_match_num = MatchNumber(self.schedule.n_league_matches)

        teams = list(self.scores.league.positions.keys())
        teams = [
            tla
            for tla in teams
            if self.teams[tla].is_still_around(first_knockout_match_num)
        ]

        if not self._played_all_league_matches():
            teams = [UNKNOWABLE_TEAM] * len(teams)

        return teams

    def _append_knockout_round(
        self,
        rounds_remaining: int,
        name: str | None = None,
    ) -> KnockoutRound:
        if name is None:
            name = self.get_round_display_name(
                round_number=len(self.knockout_rounds),
                rounds_remaining=rounds_remaining,
            )

        knockout_round = KnockoutRound(name=name)
        self.knockout_rounds.append(knockout_round)

        return knockout_round

    def add_knockouts(self) -> None:
        """
        Add the knockouts to the schedule.

        Derived classes must override this method.
        """
        raise NotImplementedError()
