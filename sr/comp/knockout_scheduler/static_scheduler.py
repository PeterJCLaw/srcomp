"""
A static knockout schedule.
"""

from ..match_period import Match, MatchType
from .base_scheduler import BaseKnockoutScheduler, UNKNOWABLE_TEAM


class StaticScheduler(BaseKnockoutScheduler):
    """
    A knockout scheduler which loads almost fixed data from the config. Assumes
    only a single arena.
    """

    def get_team(self, team_ref):
        if not self._played_all_league_matches():
            return UNKNOWABLE_TEAM

        if team_ref is None:
            return None

        if team_ref.startswith('S'):
            # get a seeded position
            positions = list(self.scores.league.positions.keys())
            pos = int(team_ref[1:])
            pos -= 1  # seed numbers are 1 based
            try:
                return positions[pos]
            except IndexError:
                raise ValueError(
                    "Cannot reference seed {}, there are only {} teams!".format(
                        team_ref,
                        len(positions),
                    ),
                )

        # get a position from a match
        assert len(team_ref) == 3
        round_num, match_num, pos = [int(x) for x in team_ref]

        try:
            match = self.knockout_rounds[round_num][match_num]
        except IndexError:
            raise ValueError(
                "Reference '{}' to unscheduled match!".format(team_ref),
            )

        try:
            ranking = self.get_ranking(match)
            return ranking[pos]
        except IndexError:
            raise ValueError(
                "Reference '{}' to invalid ranking!".format(team_ref),
            )

    def _add_match(self, match_info, rounds_remaining, round_num):
        new_matches = {}

        arena = match_info['arena']
        start_time = match_info['start_time']
        end_time = start_time + self.schedule.match_duration
        num = len(self.schedule.matches)

        teams = []
        for team_ref in match_info['teams']:
            teams.append(self.get_team(team_ref))

        if len(teams) < self.num_teams_per_arena:
            # Fill empty zones with None
            teams += [None] * (self.num_teams_per_arena-len(teams))

        display_name = self.get_match_display_name(rounds_remaining, round_num,
                                                   num)

        # allow overriding the name
        override_name = match_info.get('display_name')
        if override_name is not None:
            display_name = "{} (#{})".format(override_name, num)

        is_final = rounds_remaining == 0
        match = Match(num, display_name, arena, teams, start_time, end_time,
                      MatchType.knockout, use_resolved_ranking=not is_final)
        self.knockout_rounds[-1].append(match)

        new_matches[match_info['arena']] = match

        self.schedule.matches.append(new_matches)
        self.period.matches.append(new_matches)

    def add_knockouts(self):
        knockout_conf = self.config['static_knockout']['matches']

        for round_num, round_info in sorted(knockout_conf.items()):
            self.knockout_rounds += [[]]
            rounds_remaining = len(knockout_conf) - round_num - 1
            for match_num, match_info in sorted(round_info.items()):
                self._add_match(match_info, rounds_remaining, match_num)
