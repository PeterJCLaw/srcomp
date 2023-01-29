"""Match schedule library."""

from __future__ import annotations

import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence, TypeVar
from typing_extensions import TypedDict

import dateutil.tz
from league_ranker import RankedPosition

from . import yaml_loader
from .arenas import Arena
from .knockout_scheduler import KnockoutScheduler, StaticScheduler
from .knockout_scheduler.base_scheduler import BaseKnockoutScheduler
from .match_period import Delay, Match, MatchPeriod, MatchSlot, MatchType
from .match_period_clock import MatchPeriodClock
from .scores import Scores
from .teams import Team
from .types import (
    ArenaName,
    DelayData,
    ExtraSpacingData,
    LeagueMatches,
    MatchNumber,
    ShepherdName,
    TLA,
    YAMLData,
)

TSchedule = TypeVar('TSchedule', bound='MatchSchedule')


class StagingOffsets(TypedDict):
    opens: datetime.timedelta
    closes: datetime.timedelta
    duration: datetime.timedelta
    signal_shepherds: Mapping[ShepherdName, datetime.timedelta]
    signal_teams: datetime.timedelta


class StagingTimes(TypedDict):
    opens: datetime.datetime
    closes: datetime.datetime
    duration: datetime.timedelta
    signal_shepherds: Mapping[ShepherdName, datetime.datetime]
    signal_teams: datetime.datetime


class WrongNumberOfTeams(Exception):
    def __init__(
        self,
        match_n: int,
        arena_name: str,
        teams: Sequence[TLA | None],
        num_teams_per_arena: int,
    ) -> None:
        message = "Match {}{} has {} teams but must have {}".format(
            arena_name,
            match_n,
            len(teams),
            num_teams_per_arena,
        )
        super().__init__(message)


def parse_ranges(ranges: str) -> set[int]:
    """
    Parse a comma separated list of numbers which may include ranges
    specified as hyphen-separated numbers.

    From https://stackoverflow.com/questions/6405208
    """
    result: list[int] = []
    for part in ranges.split(','):
        if '-' in part:
            a_, b_ = part.split('-')
            a, b = int(a_), int(b_)
            result.extend(range(a, b + 1))
        else:
            a = int(part)
            result.append(a)
    return set(result)


def get_timezone(name: str) -> datetime.tzinfo:
    tzinfo = dateutil.tz.gettz(name)
    if tzinfo is None:
        raise ValueError(f"Failed to load timezone info for {name!r}")
    return tzinfo


class MatchSchedule:
    """
    A match schedule.
    """

    @classmethod
    def create(
        cls: type[TSchedule],
        config_fname: Path,
        league_fname: Path,
        scores: Scores,
        arenas: Mapping[ArenaName, Arena],
        num_teams_per_arena: int,
        teams: Mapping[TLA, Team],
    ) -> TSchedule:
        """
        Create a new match schedule around the given config data.

        :param Path config_fname: The filename of the main config file.
        :param Path league_fname: The filename of the file containing the league matches.
        :param `.Scores` scores: The scores for the competition.
        :param dict arenas: A mapping of arena ids to :class:`.Arena` instances.
        :param int num_teams_per_arena: The usual number of teams per arena.
        :param dict teams: A mapping of TLAs to :class:`.Team` instances.
        """

        y = yaml_loader.load(config_fname)

        league: LeagueMatches = yaml_loader.load(league_fname)['matches']

        schedule = cls(y, league, teams, num_teams_per_arena)

        if y['knockout'].get('static', False):
            knockout_scheduler: type[BaseKnockoutScheduler] = StaticScheduler
        else:
            knockout_scheduler = KnockoutScheduler

        k = knockout_scheduler(schedule, scores, arenas, num_teams_per_arena, teams, y)
        k.add_knockouts()

        schedule.knockout_rounds = k.knockout_rounds
        schedule.match_periods.append(k.period)

        if 'tiebreaker' in y:
            schedule.add_tiebreaker(scores, y['tiebreaker'])

        return schedule

    def __init__(
        self,
        y: YAMLData,
        league: LeagueMatches,
        teams: Mapping[TLA, Team],
        num_teams_per_arena: int,
    ) -> None:
        self._num_corners = num_teams_per_arena

        self.teams = teams
        """A mapping of TLAs to :class:`.Team` instances."""

        self.match_periods: list[MatchPeriod] = []
        r"""
        A list of the :class:`.MatchPeriod`\s which contain the matches
        for the competition.
        """

        self.knockout_rounds: list[list[Match]] = []
        """
        A list of the knockout matches by round. Each entry in the list
        represents a round of knockout matches, such that `knockout_rounds[-1]`
        contains a list with only one match -- the final.
        """

        for e in y['match_periods']['league']:
            if 'max_end_time' in e:
                max_end_time = e['max_end_time']
            else:
                max_end_time = e['end_time']

            period = MatchPeriod(
                e['start_time'],
                e['end_time'],
                max_end_time,
                e['description'],
                [],
                MatchType.league,
            )
            self.match_periods.append(period)

        self._load_match_slot_lengths(y['match_slot_lengths'])
        self._load_staging_times(y['staging'])

        self._build_extra_spacing(y['league']['extra_spacing'])
        self._build_delaylist(y['delays'])

        self.matches: list[MatchSlot] = []
        """
        A list of match slots in the schedule. Each match slot is a dict of
        arena to the :class:`.Match` occurring in that arena.
        """

        self.n_planned_league_matches = 0
        """The number of planned league matches."""

        self._build_matchlist(league)

        self.timezone = get_timezone(y.get('timezone', 'UTC'))

        self.n_league_matches = self.n_matches()

    def _load_match_slot_lengths(self, yamldata: YAMLData) -> None:
        durations = {
            key: datetime.timedelta(0, value)
            for key, value in yamldata.items()
        }
        pre = durations['pre']
        post = durations['post']
        match = durations['match']
        total = durations['total']
        if total != pre + post + match:
            raise ValueError("Match slot lengths are inconsistent.")
        self.match_slot_lengths = durations
        self.match_duration: datetime.timedelta = total

    def _load_staging_times(self, yamldata: YAMLData) -> None:
        def to_timedeltas(item: Any) -> Any:
            if isinstance(item, dict):
                return {
                    key: to_timedeltas(value)
                    for key, value in item.items()
                }
            else:
                return datetime.timedelta(seconds=item)

        durations: StagingOffsets = to_timedeltas(yamldata)

        opens = durations['opens']
        closes = durations['closes']
        duration = durations['duration']
        if duration != opens - closes:
            raise ValueError("Staging timings are inconsistent.")

        for other in ('signal_teams', 'signal_shepherds'):
            if other not in durations:
                raise ValueError(f"Staging times missing {other!r} key.")

        self.staging_times = durations

    def get_staging_times(self, match: Match) -> StagingTimes:
        pre = self.match_slot_lengths['pre']
        match_start = match.start_time + pre
        offsets = self.staging_times

        signal_shepherds: dict[ShepherdName, datetime.datetime] = {
            area: match_start - offset
            for area, offset in offsets['signal_shepherds'].items()
        }

        return {
            'opens': match_start - offsets['opens'],
            'closes': match_start - offsets['closes'],
            'duration': self.staging_times['duration'],
            'signal_shepherds': signal_shepherds,
            'signal_teams': match_start - offsets['signal_teams'],
        }

    def _build_extra_spacing(self, yamldata: list[ExtraSpacingData] | None) -> None:
        spacing: dict[MatchNumber, datetime.timedelta] = {}
        if not yamldata:
            self._spacing = spacing
            return

        for info in yamldata:
            match_numbers = parse_ranges(info['match_numbers'])
            duration = timedelta(seconds=info['duration'])
            for num in match_numbers:
                assert num not in spacing
                spacing[MatchNumber(num)] = duration

        self._spacing = spacing

    def _build_delaylist(self, yamldata: list[DelayData] | None) -> None:
        delays: list[Delay] = []
        if yamldata is None:
            # No delays, hurrah
            self.delays = delays
            return

        for info in yamldata:
            d = Delay(timedelta(seconds=info['delay']), info['time'])
            delays.append(d)

        delays.sort(key=lambda x: x.time)
        self.delays = delays

    def remove_drop_outs(
        self,
        teams: Iterable[TLA | None],
        since_match: MatchNumber,
    ) -> list[TLA | None]:
        """
        Take a list of TLAs and replace the teams that have dropped out with
        ``None`` values.

        :param list teams: A list of TLAs.
        :param int since_match: The match number to check for drop outs from.
        :return: A new list containing the appropriate teams.
        """
        new_teams: list[TLA | None] = []
        for tla in teams:
            if tla is None:
                new_teams.append(None)
            else:
                if self.teams[tla].is_still_around(since_match):
                    new_teams.append(tla)
                else:
                    new_teams.append(None)
        return new_teams

    def _build_matchlist(self, yamldata: LeagueMatches | None) -> None:
        """
        Build the match list.

        :param dict yamldata: The matches data from the league file, formatted
        as a dict of match numbers to dicts of arena to lists of TLAs.
        """

        if yamldata is None:
            return

        match_numbers = sorted(yamldata.keys())
        self.n_planned_league_matches = len(match_numbers)

        if tuple(match_numbers) != tuple(range(len(match_numbers))):
            raise Exception("Matches are not a complete 0-N range")

        # Effectively just the .values(), except that it's ordered by number
        raw_matches = [yamldata[m] for m in match_numbers]

        match_n = MatchNumber(0)

        for period in self.match_periods:
            # Fill this period with matches

            clock = MatchPeriodClock(period, self.delays)

            # No extra spacing for matches at the start of a period

            # Fill this match period with matches
            for start in clock.iterslots(self.match_duration):
                try:
                    arenas = raw_matches.pop(0)
                except IndexError:
                    # no more matches left
                    break

                match_slot = self._create_league_match_slot(start, arenas, match_n)
                period.matches.append(match_slot)
                self.matches.append(match_slot)

                match_n = MatchNumber(match_n + 1)

                extra_spacing = self._spacing.get(match_n)
                if extra_spacing:
                    clock.advance_time(extra_spacing)

    def _create_league_match_slot(
        self,
        start_time: datetime.datetime,
        arenas: Mapping[ArenaName, Sequence[TLA | None]],
        match_n: MatchNumber,
    ) -> MatchSlot:
        """
        Returns a dict of arena to :class:`.Match` for the given start time,
        arenas dict and match number.
        """
        match_slot: dict[ArenaName, Match] = {}

        end_time = start_time + self.match_duration
        for arena_name, teams in arenas.items():
            teams = self.remove_drop_outs(teams, match_n)
            display_name = f"Match {match_n}"

            if len(teams) != self._num_corners:
                raise WrongNumberOfTeams(match_n, arena_name, teams, self._num_corners)

            match = Match(
                match_n,
                display_name,
                arena_name,
                teams,
                start_time,
                end_time,
                MatchType.league,
                use_resolved_ranking=False,
            )
            match_slot[arena_name] = match

        return MatchSlot(match_slot)

    def delay_at(self, date: datetime.datetime) -> datetime.timedelta:
        """
        Calculates the active delay at a given ``date``. Intended for use
        only in exposing the current delay value -- scheduling should be
        done using a :class:`.MatchPeriodClock` instead.

        :param datetime date: The date to find the delay for.
        :return: A :class:`datetime.timedelta` specifying the active delay.
        """

        total = timedelta()
        period = self.period_at(date)
        if not period:
            # No current period, no delays active
            return total

        delays = MatchPeriodClock.delays_for_period(period, self.delays)
        for delay in delays:
            if delay.time > date:
                break

            total += delay.delay

        return total

    def matches_at(self, date: datetime.datetime) -> Iterator[Match]:
        """
        Get all the matches that occur around a specific ``date``.

        :param datetime date: The date at which matches occur.
        :return: An iterable list of matches.
        """

        for slot in self.matches:
            for match in slot.values():
                if match.start_time <= date < match.end_time:
                    yield match

    def period_at(self, date: datetime.datetime) -> MatchPeriod | None:
        """
        Get the match period that occur around a specific ``date``.

        :param datetime date: The date at which period occurs.
        :return: The period at that time or ``None``.
        """

        for period in self.match_periods:
            if period.start_time <= date < period.max_end_time:
                return period

        return None

    def n_matches(self) -> int:
        """
        Get the number of matches.

        :return: The number of matches.
        """

        return len(self.matches)

    @property
    def final_match(self) -> Match:
        """
        Get the :class:`.Match` for the last match of the competition.

        This is the info for the 'finals' of the competition (i.e: the
        last of the knockout matches) unless there is a tiebreaker.
        """
        last_match_slot = self.matches[-1]
        last_matches = list(last_match_slot.values())
        assert len(last_matches) == 1, last_match_slot
        return last_matches[0]

    def add_tiebreaker(self, scores: Scores, time: datetime.datetime) -> None:
        """
        Add a tie breaker to the league if required. Also set a ``tiebreaker``
        attribute if necessary.

        :param `.Scores` scores: The scores for the competition.
        :param datetime.datetime time: The time to have the tiebreaker match.
        """

        finals_info = self.knockout_rounds[-1][0]
        finals_key = (finals_info.arena, finals_info.num)
        try:
            finals_positions = scores.knockout.game_positions[finals_key]
        except KeyError:
            return
        winners = finals_positions.get(RankedPosition(1))
        if not winners:
            raise AssertionError("The only winning move is not to play.")
        if len(winners) > 1:  # Act surprised!
            # Start with the winning teams in the same order as in the finals
            tiebreaker_teams = [
                team if team in winners else None
                for team in finals_info.teams
            ]
            # Use a static permutation
            permutation = [3, 2, 0, 1]
            tiebreaker_teams = [
                tiebreaker_teams[permutation[n]]
                for n in permutation
            ]
            # Inject new match
            end_time = time + self.match_duration
            num = self.n_matches()
            arena = finals_info.arena
            match = Match(
                num=MatchNumber(num),
                display_name=f"Tiebreaker (#{num})",
                arena=arena,
                teams=tiebreaker_teams,
                type=MatchType.tiebreaker,
                start_time=time,
                end_time=end_time,
                use_resolved_ranking=False,
            )
            slot = MatchSlot({arena: match})
            self.matches.append(slot)
            match_period = MatchPeriod(
                time,
                end_time,
                end_time,
                'Tiebreaker',
                [slot],
                MatchType.tiebreaker,
            )
            self.match_periods.append(match_period)

            self.tiebreaker = match

    @property
    def datetime_now(self) -> datetime.datetime:
        """Get the current date and time, with the correct timezone."""
        return datetime.datetime.now(self.timezone)
