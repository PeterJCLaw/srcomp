"""An automatic seeded knockout schedule."""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Iterable, Mapping, Sized, TYPE_CHECKING

from ..match_period import Match, MatchSlot, MatchType
from ..match_period_clock import MatchPeriodClock, OutOfTimeException
from ..scores import Scores
from ..teams import Team
from ..types import ArenaName, MatchNumber, TLA, YAMLData
from . import seeding, stable_random
from .base_scheduler import BaseKnockoutScheduler, UNKNOWABLE_TEAM

if TYPE_CHECKING:
    # Circular
    from ..matches import MatchSchedule


class KnockoutScheduler(BaseKnockoutScheduler):
    """
    A class that can be used to generate a knockout schedule based on seeding.

    Due to the way the seeding logic works, this class is suitable only when
    games feature four slots for competitors, with the top two progressing to
    the next round.

    :param schedule: The league schedule.
    :param scores: The scores.
    :param dict arenas: The arenas.
    :param int num_teams_per_arena: The usual number of teams per arena.
    :param dict teams: The teams.
    :param config: Custom configuration for the knockout scheduler.
    """

    num_teams_per_arena = 4
    """
    Constant value due to the way the automatic seeding works.
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
        if num_teams_per_arena != self.num_teams_per_arena:
            raise ValueError(
                "The automatic knockout scheduler can only be used for {} teams"
                " per arena (and not {})".format(
                    self.num_teams_per_arena,
                    num_teams_per_arena,
                ),
            )

        super().__init__(schedule, scores, arenas, num_teams_per_arena, teams, config)

        self.R = stable_random.Random()

        self.clock = MatchPeriodClock(self.period, self.schedule.delays)

    def _add_round_of_matches(
        self,
        matches: list[list[TLA]],
        arenas: Iterable[ArenaName],
        rounds_remaining: int,
    ) -> None:
        """
        Add a whole round of matches.

        :param list matches: A list of lists of teams for each match.
        """

        self.knockout_rounds += [[]]

        round_num = 0
        while len(matches):
            # Deliberately not using iterslots since we need to ensure
            # that the time advances even after we've run out of matches
            start_time = self.clock.current_time
            end_time = start_time + self.schedule.match_duration

            new_matches = {}
            for arena in arenas:
                teams: list[TLA | None] = list(matches.pop(0))

                if len(teams) < self.num_teams_per_arena:
                    # Fill empty zones with None
                    teams += [None] * (self.num_teams_per_arena - len(teams))

                # Randomise the zones
                self.R.shuffle(teams)

                num = MatchNumber(len(self.schedule.matches))
                display_name = self.get_match_display_name(
                    rounds_remaining,
                    round_num,
                    num,
                )

                match = Match(
                    num,
                    display_name,
                    arena,
                    teams,
                    start_time,
                    end_time,
                    MatchType.knockout,
                    # Just the finals don't use the resolved ranking
                    use_resolved_ranking=rounds_remaining != 0,
                )

                self.knockout_rounds[-1].append(match)
                new_matches[arena] = match

                if len(matches) == 0:
                    break

            self.clock.advance_time(self.schedule.match_duration)
            self.schedule.matches.append(MatchSlot(new_matches))
            self.period.matches.append(MatchSlot(new_matches))

            round_num += 1

    def get_winners(self, game: Match) -> list[TLA]:
        """
        Find the parent match's winners.

        :param game: A game.
        """

        ranking = self.get_ranking(game)
        return ranking[:2]

    def _add_round(self, arenas: Iterable[ArenaName], rounds_remaining: int) -> None:
        prev_round = self.knockout_rounds[-1]
        matches = []

        for i in range(0, len(prev_round), 2):
            winners = []
            for parent in prev_round[i:i + 2]:
                winners += self.get_winners(parent)

            matches.append(winners)

        self._add_round_of_matches(matches, arenas, rounds_remaining)

    def _add_first_round(self, conf_arity: int | None = None) -> None:
        next_match_num = len(self.schedule.matches)
        teams = self._get_non_dropped_out_teams(MatchNumber(next_match_num))
        if not self._played_all_league_matches():
            teams = [UNKNOWABLE_TEAM] * len(teams)

        arity = len(teams)
        if conf_arity is not None and conf_arity < arity:
            arity = conf_arity

        # Seed the random generator with the seeded team list
        # This makes it unpredictable which teams will be in which zones
        # until the league scores have been established
        self.R.seed(''.join(teams).encode('utf-8'))

        matches = []

        for seeds in seeding.first_round_seeding(arity):
            match_teams = [teams[seed] for seed in seeds]
            matches.append(match_teams)

        rounds_remaining = self.get_rounds_remaining(matches)
        self._add_round_of_matches(matches, self.arenas, rounds_remaining)

    @staticmethod
    def get_rounds_remaining(prev_matches: Sized) -> int:
        return int(math.log(len(prev_matches), 2))

    def _add_knockouts(self) -> None:
        knockout_conf = self.config['knockout']
        round_spacing = timedelta(seconds=knockout_conf['round_spacing'])

        self._add_first_round(conf_arity=knockout_conf.get('arity'))

        while len(self.knockout_rounds[-1]) > 1:

            # Add the delay between rounds
            self.clock.advance_time(round_spacing)

            # Number of rounds remaining to be added
            rounds_remaining = self.get_rounds_remaining(self.knockout_rounds[-1])

            if rounds_remaining <= knockout_conf['single_arena']['rounds']:
                arenas = knockout_conf['single_arena']['arenas']
            else:
                arenas = self.arenas

            if len(self.knockout_rounds[-1]) == 2:
                # Extra delay before the final match
                final_delay = timedelta(seconds=knockout_conf['final_delay'])
                self.clock.advance_time(final_delay)

            self._add_round(arenas, rounds_remaining - 1)

    def add_knockouts(self) -> None:
        try:
            self._add_knockouts()
        except OutOfTimeException as e:
            raise OutOfTimeException(
                "Ran out of time scheduling the knockouts. This usually indicates "
                "that there are more teams than it is possible to schedule matches "
                "for within the given period. Consider adjusting the number of teams "
                "which progress to the knockouts or allowing more time.",
            ) from e
