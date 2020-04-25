"""Compstate validation routines."""

import datetime
import sys
from collections import defaultdict
from typing import (
    Container,
    Iterable,
    List,
    Mapping,
    NewType,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from .comp import SRComp
from .knockout_scheduler import UNKNOWABLE_TEAM
from .match_period import Match, MatchSlot, MatchType
from .matches import MatchSchedule
from .scores import BaseScores
from .types import ArenaName, MatchId, MatchNumber, TLA

Errors = List[str]
ErrorType = NewType('ErrorType', str)

NO_TEAM = None
META_TEAMS = set([NO_TEAM, UNKNOWABLE_TEAM])


def join_and(items: Iterable[object]) -> str:
    strings = [str(x) for x in items]
    if not strings:
        return ""

    if len(strings) == 1:
        return strings[0]

    *rest, last = strings

    return " and ".join((", ".join(rest), last))


def report_errors(type_: ErrorType, id_: object, errors: Errors) -> None:
    """
    Print out errors nicely formatted.

    :param str type: The human-readable 'type'.
    :param str id_: The human-readable 'ID'.
    :param list errors: A list of string errors.
    """

    if len(errors) == 0:
        return

    print(
        "{0} {1} has the following errors:".format(type_, id_),
        file=sys.stderr,
    )
    for error in errors:
        print("    {0}".format(error), file=sys.stderr)


def validate(comp: SRComp) -> int:
    """
    Validate a Compstate repo.

    :param sr.comp.SRComp comp: A competition instance.
    :return: The number of errors that have occurred.
    """

    count = 0
    count += validate_schedule(comp.schedule, comp.teams.keys(), comp.arenas.keys())

    all_matches = comp.schedule.matches
    count += validate_team_matches(all_matches, comp.teams.keys())

    count += validate_scores(MatchType.league, comp.scores.league, all_matches)
    count += validate_scores(MatchType.knockout, comp.scores.knockout, all_matches)
    count += validate_scores(MatchType.tiebreaker, comp.scores.tiebreaker, all_matches)

    return count


def validate_schedule(
    schedule: MatchSchedule,
    possible_teams: Iterable[TLA],
    possible_arenas: Container[ArenaName],
) -> int:
    """Check that the schedule contains enough time for all the matches,
    and that the matches themselves are valid."""
    count = 0

    # Check that each match features only valid teams
    for num, match in enumerate(schedule.matches):
        errors = validate_match(match, possible_teams)
        count += len(errors)
        report_errors(ErrorType('Match'), num, errors)

    warnings = validate_schedule_count(schedule)
    report_errors(ErrorType('Schedule'), '', warnings)

    errors = validate_schedule_timings(schedule.matches, schedule.match_duration)
    count += len(errors)
    if len(errors):
        errors.append(
            "This usually indicates that the scheduled periods overlap.",
        )
    report_errors(ErrorType('Schedule'), 'timing', errors)

    errors = validate_schedule_arenas(schedule.matches, possible_arenas)
    count += len(errors)
    report_errors(ErrorType('Schedule'), 'arenas', errors)

    return count


def validate_schedule_count(schedule: MatchSchedule) -> Errors:
    planned = schedule.n_planned_league_matches
    actual = schedule.n_league_matches
    errors = []
    if planned > actual:
        msg = "Only contains enough time for {0} matches, {1} are planned".format(
            actual,
            planned,
        )
        errors.append(msg)
    if planned == 0:
        errors.append("Doesn't contain any matches")

    return errors


def validate_schedule_timings(
    scheduled_matches: Iterable[MatchSlot],
    match_duration: datetime.timedelta,
) -> Errors:
    timing_map = defaultdict(list)
    for match in scheduled_matches:
        game = list(match.values())[0]
        time = game.start_time
        timing_map[time].append(game.num)

    errors = []
    last_time = None  # type: Optional[datetime.datetime]
    for time, match_numbers in sorted(timing_map.items()):
        if len(match_numbers) != 1:
            errors.append("Multiple matches scheduled for {0}: {1}.".format(
                time,
                join_and(match_numbers),
            ))

        if last_time is not None and time - last_time < match_duration:
            errors.append("Matches {0} start at {1} before matches {2} have finished.".format(
                join_and(match_numbers),
                time,
                join_and(timing_map[last_time]),
            ))

        last_time = time

    return errors


def validate_schedule_arenas(
    matches: Iterable[MatchSlot],
    possible_arenas: Container[ArenaName],
) -> Errors:
    """Check that any arena referenced by a match actually exists."""
    errors = []
    error_format_string = "Match {game.num} ({game.type}) references arena '{arena}'."

    for match in matches:
        for arena, game in match.items():
            if arena not in possible_arenas:
                errors.append(error_format_string.format(
                    arena=arena,
                    game=game,
                ))

    return errors


def validate_match(match: MatchSlot, possible_teams: Iterable[TLA]) -> Errors:
    """Check that the teams featuring in a match exist and are only
    required in one arena at a time."""
    errors = []
    all_teams = []  # type: List[Optional[TLA]]

    for a in match.values():
        all_teams += a.teams

    teams = set(all_teams) - META_TEAMS
    for t in teams:
        all_teams.remove(t)

    # Note: mypy doesn't know that removing META_TEAMS here means that we're
    # removing the Optional nature of the teams.
    # See https://github.com/python/mypy/issues/8526.
    duplicates = set(all_teams) - META_TEAMS  # type: Set[TLA]  # type: ignore[assignment]
    if len(duplicates):
        errors.append("Teams {0} appear more than once.".format(
            join_and(duplicates),
        ))

    extras = teams - set(possible_teams)

    if len(extras):
        errors.append("Teams {0} do not exist.".format(
            join_and(extras),
        ))

    return errors


def validate_scores(
    match_type: MatchType,
    scores: BaseScores,
    schedule: Sequence[MatchSlot],
) -> int:
    """Validate that the scores are sane."""
    count = validate_scores_inner(match_type, scores, schedule)
    warn_missing_scores(match_type, scores, schedule)
    return count


def validate_scores_inner(
    match_type: MatchType,
    scores: BaseScores,
    schedule: Sequence[MatchSlot],
) -> int:
    """Validate that scores are sane."""
    # NB: more specific validation is already done during the scoring,
    # so all we need to do is check that the right teams are being awarded
    # points

    count = 0
    match_type_title = match_type.name.title()

    def get_scheduled_match(match_id: MatchId, type_: ErrorType) -> Optional[Match]:
        """Check that the requested match was scheduled, return it if so."""
        num = match_id[1]
        if num < 0 or num >= len(schedule):
            msg = "{0} Match not scheduled".format(match_type_title)
            report_errors(type_, match_id, [msg])
            return None

        arena = match_id[0]
        match = schedule[num]
        if arena not in match:
            msg = "Arena not in this {0} match".format(match_type_title)
            report_errors(type_, match_id, [msg])
            return None

        return match[arena]

    def check(type_: ErrorType, match_id: MatchId, match: Mapping[TLA, object]) -> int:
        scheduled_match = get_scheduled_match(match_id, type_)
        if scheduled_match is None:
            return 1

        errors = validate_match_score(match_type, match, scheduled_match)
        report_errors(type_, match_id, errors)
        return len(errors)

    for match_id, game_points in scores.game_points.items():
        count += check(ErrorType('Game Score'), match_id, game_points)

    if match_type == MatchType.league:
        for match_id, league_points in scores.ranked_points.items():
            count += check(ErrorType('League Points'), match_id, league_points)

    return count


def validate_match_score(
    match_type: MatchType,
    match_score: Mapping[TLA, object],
    scheduled_match: Match,
) -> Errors:
    """Check that the match awards points to the right teams, by checking
    that the teams with points were scheduled to appear in the match."""
    # only remove the empty corner marker -- we shouldn't have unknowable
    # teams in the match schedule by the time there's a score for it.
    expected_teams = set(x for x in scheduled_match.teams if x is not NO_TEAM)
    # don't remove meta teams from the score's teams -- they shouldn't
    # be there to start with.
    actual_teams = set(match_score.keys())

    extra = actual_teams - expected_teams
    missing = expected_teams - actual_teams

    errors = []
    if len(missing):
        errors.append("Teams {0} missing from this {1} match.".format(
            join_and(missing),
            match_type.name,
        ))

    if len(extra):
        errors.append("Teams {0} not scheduled in this {1} match.".format(
            join_and(extra),
            match_type.name,
        ))

    return errors


def warn_missing_scores(
    match_type: MatchType,
    scores: BaseScores,
    schedule: Iterable[MatchSlot],
) -> None:
    """Check that the scores up to the most recent are all present."""
    match_ids = scores.ranked_points.keys()
    last_match = scores.last_scored_match

    missing = find_missing_scores(match_type, match_ids, last_match, schedule)
    if len(missing) == 0:
        return

    msg = "The following {0} scores are missing:".format(match_type.name)
    print(msg, file=sys.stderr)
    print("Match   | Arena ", file=sys.stderr)
    for m in missing:
        arenas = join_and(sorted(m[1]))
        print(" {0:>3}    | {1}".format(m[0], arenas), file=sys.stderr)


def find_missing_scores(
    match_type: MatchType,
    match_ids: Iterable[MatchId],
    last_match: Optional[int],
    schedule: Iterable[MatchSlot],
) -> Sequence[Tuple[MatchNumber, Set[ArenaName]]]:
    """
    Given a collection of ``match_ids`` for which we have scores, the
    ``match_type`` currently under consideration, the number of the
    ``last_match`` which was scored and the list of all known matches determine
    which scores should be present but aren't.
    """

    # If no matches have been scored, no scores can be missing.
    if last_match is None:
        return ()

    expected = set()
    for num, match in enumerate(schedule):
        if num > last_match:
            break
        for arena, game in match.items():
            # Filter to the right type of matches -- we only ever deal
            # with one type at a time
            if game.type == match_type:
                id_ = (arena, game.num)
                expected.add(id_)

    missing_ids = expected - set(match_ids)
    missing = defaultdict(set)
    for id_ in missing_ids:
        arena = id_[0]
        num = id_[1]
        missing[num].add(arena)

    missing_items = sorted(missing.items())
    return missing_items


def validate_team_matches(
    matches: Iterable[MatchSlot],
    possible_teams: Iterable[TLA],
) -> int:
    """
    Check that all teams have been assigned league matches. We don't need (or
    want) to check the knockouts, since those are scheduled dynamically based
    on the list of teams.
    """

    teams_without_matches = find_teams_without_league_matches(
        matches,
        possible_teams,
    )
    if teams_without_matches:
        print("The following teams have no league matches: {0}".format(
            join_and(sorted(teams_without_matches)),
        ))

    return len(teams_without_matches)


def find_teams_without_league_matches(
    matches: Iterable[MatchSlot],
    possible_teams: Iterable[TLA],
) -> Set[TLA]:
    """
    Find teams that don't have league matches.

    :param list matches: A list of matches.
    :param possible_teams: A list of possible teams.
    :return: A :class:`set` of teams without matches.
    """
    teams_used = set()
    for match in matches:
        for game in match.values():
            if game.type == MatchType.league:
                teams_used |= set(game.teams)

    teams_without_matches = set(possible_teams) - teams_used

    return teams_without_matches
