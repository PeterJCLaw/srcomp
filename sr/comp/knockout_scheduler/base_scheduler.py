"""Base for knockout scheduling."""

from __future__ import annotations

from typing import Iterable, Mapping, TYPE_CHECKING

from ..match_period import Match, MatchPeriod, MatchType
from ..scores import Scores
from ..teams import Team
from ..types import ArenaName, MatchNumber, TLA, YAMLData

if TYPE_CHECKING:
    # Circular
    from ..matches import MatchSchedule

# Use '???' as the "we don't know yet" marker
UNKNOWABLE_TEAM = TLA('???')


class BaseKnockoutScheduler:
    """
    Base class for knockout schedulers offering common functionality.

    :param schedule: The league schedule.
    :param scores: The scores.
    :param dict arenas: The arenas.
    :param dict teams: The teams.
    :param config: Custom configuration for the knockout scheduler.
    """

    def __init__(
        self,
        schedule: MatchSchedule,
        scores: Scores,
        arenas: Iterable[ArenaName],
        num_teams_per_arena: int,
        teams: Mapping[TLA, Team],
        config: YAMLData,
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

        # The knockout matches appear in the normal matches list
        # but this list provides them in groups of rounds.
        # e.g. self.knockout_rounds[-2] gives the semi-final matches
        # and self.knockout_rounds[-1] gives the final match (in a list)
        # Note that the ordering of the matches within the rounds
        # in this list is important (e.g. self.knockout_rounds[0][0] is
        # will involve the top seed, whilst self.knockout_rounds[0][-1] will
        # involve the second seed).
        self.knockout_rounds: list[list[Match]] = []

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

                if (match.arena, match.num) not in \
                        self.scores.league.game_points:
                    return False

        return True

    @staticmethod
    def get_match_display_name(
        rounds_remaining: int,
        round_num: int,
        global_num: MatchNumber,
    ) -> str:
        """
        Get a human-readable match display name.

        :param rounds_remaining: The number of knockout rounds remaining.
        :param knockout_num: The match number within the knockout round.
        :param global_num: The global match number.
        """

        if rounds_remaining == 0:
            display_name = "Final (#{global_num})"
        elif rounds_remaining == 1:
            display_name = "Semi {round_num} (#{global_num})"
        elif rounds_remaining == 2:
            display_name = "Quarter {round_num} (#{global_num})"
        else:
            display_name = "Match {global_num}"
        return display_name.format(
            round_num=round_num + 1,
            global_num=global_num,
        )

    def get_ranking(self, game: Match) -> list[TLA]:
        """
        Get a ranking of the given match's teams.

        :param game: A game.
        """
        desc = (game.arena, game.num)

        # Get the resolved positions if present (will be a tla -> position map)
        positions = self.scores.knockout.resolved_positions.get(desc, None)

        if positions is None:
            # Given match hasn't been scored yet
            return [UNKNOWABLE_TEAM] * self.num_teams_per_arena

        # Extract just TLAs
        return list(positions.keys())

    def _get_non_dropped_out_teams(self, for_match: MatchNumber) -> list[TLA]:
        teams = list(self.scores.league.positions.keys())
        teams = [
            tla
            for tla in teams
            if self.teams[tla].is_still_around(for_match)
        ]
        return teams

    def add_knockouts(self) -> None:
        """
        Add the knockouts to the schedule.

        Derived classes must override this method.
        """
        raise NotImplementedError()
